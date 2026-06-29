"""
Prefect を使った ETL パイプライン。

@task  : Extract / Transform / Load の各ステップを個別のタスクとして定義する。
         失敗時のリトライ設定もここで行う。
@flow  : タスクを順番に呼び出すパイプライン全体を定義する。
         Prefect UI から実行履歴・ログ・スケジュールを管理できる。
"""

from datetime import date

import pandas as pd
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from prefect.logging import get_run_logger

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

CSV_PATH = "data/orders.csv"
JOB_NAME = "orders_etl"


# ---------------------------------------------------------------------------
# タスク定義
# ---------------------------------------------------------------------------

@task(name="setup-schema", retries=2, retry_delay_seconds=5, cache_policy=NO_CACHE)
def setup_schema_task(engine) -> None:
    """orders / watermarks / dim・fact テーブルをまとめて準備する。"""
    logger = get_run_logger()
    create_table(engine)
    create_watermark_table(engine)
    create_dwh_tables(engine)
    logger.info("スキーマ準備が完了しました。")


@task(name="get-watermark", retries=2, retry_delay_seconds=5, cache_policy=NO_CACHE)
def get_watermark_task(engine) -> date | None:
    """前回の最終取込日を取得する。初回は None を返す。"""
    logger = get_run_logger()
    last_loaded = get_watermark(engine, JOB_NAME)
    if last_loaded:
        logger.info(f"前回最終取込日: {last_loaded}（増分モード）")
    else:
        logger.info("初回実行（全件モード）")
    return last_loaded


@task(name="extract")
def extract_task(csv_path: str, since: date | None) -> pd.DataFrame:
    """CSV から増分データを読み込む。"""
    logger = get_run_logger()
    df = read_orders_csv(csv_path, since=since)
    logger.info(f"{len(df)} 件を抽出しました。")
    return df


@task(name="validate")
def validate_task(df: pd.DataFrame) -> pd.DataFrame:
    """Pydantic + Pandera でデータを検証し、正常行だけを返す。"""
    logger = get_run_logger()
    df = validate_orders(df)
    logger.info(f"検証完了: {len(df)} 件が通過しました。")
    return df


@task(name="load-staging", retries=3, retry_delay_seconds=10, cache_policy=NO_CACHE)
def load_staging_task(df: pd.DataFrame, engine) -> None:
    """orders ステージングテーブルへ Upsert する。"""
    logger = get_run_logger()
    upsert_orders(df, engine)
    logger.info(f"ステージング: {len(df)} 件をロードしました。")


@task(name="load-dwh", retries=3, retry_delay_seconds=10, cache_policy=NO_CACHE)
def load_dwh_task(engine) -> None:
    """dim / fact テーブルへ Upsert する（dim → fact の順）。"""
    logger = get_run_logger()
    upsert_dim_customer(engine)
    upsert_dim_product(engine)
    upsert_dim_date(engine)
    upsert_fact_orders(engine)
    logger.info("DWH への書き込みが完了しました。")


@task(name="update-watermark", retries=2, retry_delay_seconds=5, cache_policy=NO_CACHE)
def update_watermark_task(engine, new_watermark: date) -> None:
    """最終取込日を更新する。"""
    logger = get_run_logger()
    update_watermark(engine, JOB_NAME, new_watermark)
    logger.info(f"Watermark を {new_watermark} に更新しました。")


# ---------------------------------------------------------------------------
# フロー定義
# ---------------------------------------------------------------------------

def on_flow_failure(flow, flow_run, state) -> None:
    """フロー失敗時に呼ばれるフック。通知を送信する。"""
    notifier = get_notifier()
    notifier.send(
        title=f"ETL 失敗: {flow.name}",
        message=f"Flow Run: {flow_run.name}\n状態: {state.message}",
        level="error",
    )


@flow(name="orders-etl-pipeline", log_prints=True, on_failure=[on_flow_failure])
def etl_pipeline(csv_path: str = CSV_PATH) -> None:
    """
    注文データの ETL パイプライン。

    1. スキーマ準備
    2. Watermark 取得（増分 or 全件の判定）
    3. Extract
    4. Validate
    5. Load ステージング
    6. Load DWH
    7. Watermark 更新
    """
    engine = get_engine()

    setup_schema_task(engine)
    last_loaded = get_watermark_task(engine)
    df = extract_task(csv_path, last_loaded)

    if df.empty:
        print("新規データなし。ETL をスキップします。")
        return

    df = validate_task(df)
    load_staging_task(df, engine)
    load_dwh_task(engine)

    new_watermark = df["order_date"].dt.date.max()
    update_watermark_task(engine, new_watermark)


if __name__ == "__main__":
    etl_pipeline()
