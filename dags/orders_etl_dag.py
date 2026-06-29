"""
Airflow 版 ETL パイプライン（STEP 9-A）

pipeline.py（Prefect 版）と同じ ETL を Airflow の DAG として実装する。
TaskFlow API（@task デコレータ）を使うことで、Prefect に近い書き方になる。

Prefect との主な違い:
  - @flow → @dag
  - @task → @task（同名だが Airflow の import）
  - タスク間の依存は >> 演算子 または 引数渡し（XCom）で定義する
  - DataFrame はそのまま渡せず、dict のリストに変換して XCom 経由で受け渡す
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
from airflow.decorators import dag, task

from src.extract.reader import read_orders_csv
from src.load.dwh_loader import (
    create_dwh_tables,
    upsert_dim_customer,
    upsert_dim_date,
    upsert_dim_product,
    upsert_fact_orders,
)
from src.load.watermark import create_watermark_table, get_watermark, update_watermark
from src.load.writer import create_table, get_engine, upsert_orders
from src.notify.factory import get_notifier
from src.transform.validator import validate_orders

CSV_PATH = "/opt/airflow/project/data/orders.csv"
JOB_NAME = "orders_etl"


# ---------------------------------------------------------------------------
# 失敗時コールバック
# ---------------------------------------------------------------------------

def notify_on_failure(context: dict) -> None:
    """タスク失敗時に呼ばれる。get_notifier() で通知先を切り替えられる。"""
    notifier = get_notifier()
    dag_id = context["dag"].dag_id
    task_id = context["task_instance"].task_id
    exception = context.get("exception", "不明なエラー")
    notifier.send(
        title=f"ETL 失敗: {dag_id} / {task_id}",
        message=str(exception),
        level="error",
    )


# ---------------------------------------------------------------------------
# DAG 定義
# ---------------------------------------------------------------------------

@dag(
    dag_id="orders_etl",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",      # 毎日1回実行
    catchup=False,          # 過去分の自動バックフィルはしない
    default_args={
        "retries": 2,
        "retry_delay": timedelta(seconds=5),
        "on_failure_callback": notify_on_failure,
    },
    tags=["etl", "orders"],
)
def orders_etl_dag() -> None:
    """
    注文データの ETL パイプライン（Airflow 版）

    1. スキーマ準備
    2. Watermark 取得
    3. Extract（増分）
    4. Validate
    5. Load ステージング
    6. Load DWH
    7. Watermark 更新
    """

    # -----------------------------------------------------------------------
    # タスク定義
    # -----------------------------------------------------------------------

    @task(task_id="setup_schema")
    def setup_schema() -> None:
        engine = get_engine()
        create_table(engine)
        create_watermark_table(engine)
        create_dwh_tables(engine)

    @task(task_id="get_watermark")
    def get_watermark_task() -> str | None:
        """前回の最終取込日を文字列で返す（XCom は JSON のため date → str に変換）。"""
        engine = get_engine()
        last_loaded = get_watermark(engine, JOB_NAME)
        return str(last_loaded) if last_loaded else None

    @task(task_id="extract")
    def extract(since_str: str | None) -> list[dict]:
        """
        CSV から増分データを読み込む。
        DataFrame はそのまま XCom に乗せられないため dict のリストに変換する。
        order_date も JSON シリアライズできるよう文字列にする。
        """
        since = date.fromisoformat(since_str) if since_str else None
        df = read_orders_csv(CSV_PATH, since=since)
        if df.empty:
            return []
        df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
        return df.to_dict(orient="records")

    @task(task_id="validate")
    def validate(records: list[dict]) -> list[dict]:
        if not records:
            return []
        df = pd.DataFrame(records)
        df["order_date"] = pd.to_datetime(df["order_date"])
        df = validate_orders(df)
        df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
        return df.to_dict(orient="records")

    @task(task_id="load_staging", retries=3, retry_delay=timedelta(seconds=10))
    def load_staging(records: list[dict]) -> None:
        if not records:
            return
        df = pd.DataFrame(records)
        df["order_date"] = pd.to_datetime(df["order_date"])
        engine = get_engine()
        upsert_orders(df, engine)

    @task(task_id="load_dwh", retries=3, retry_delay=timedelta(seconds=10))
    def load_dwh() -> None:
        engine = get_engine()
        upsert_dim_customer(engine)
        upsert_dim_product(engine)
        upsert_dim_date(engine)
        upsert_fact_orders(engine)

    @task(task_id="update_watermark")
    def update_watermark_task(records: list[dict], _: None = None) -> None:
        """
        _ は load_dwh の戻り値（None）。
        値は使わないが引数に取ることで「load_dwh の後に実行する」依存関係を表現する。
        """
        if not records:
            return
        new_wm = date.fromisoformat(max(r["order_date"] for r in records))
        engine = get_engine()
        update_watermark(engine, JOB_NAME, new_wm)

    # -----------------------------------------------------------------------
    # タスクグラフの定義（依存関係）
    # -----------------------------------------------------------------------
    #
    # setup_schema → get_watermark → extract → validate → load_staging
    #                                                              ↓
    #                                               load_dwh → update_watermark
    #
    # 引数渡し（XCom）で自動的に依存関係が作られる。
    # >> は引数で表現できない順序制約だけに使う。

    schema_done = setup_schema()
    last_loaded = get_watermark_task()
    schema_done >> last_loaded                   # setup_schema が終わってから watermark を取得

    records = extract(last_loaded)
    validated = validate(records)
    staging_done = load_staging(validated)

    dwh_done = load_dwh()
    staging_done >> dwh_done                     # staging が終わってから DWH をロード

    update_watermark_task(validated, dwh_done)   # DWH 完了後に watermark を更新


orders_etl_dag()
