# Airflow vs Prefect 比較ガイド

このプロジェクトでは同じ ETL を Prefect（`pipeline.py`）と Airflow（`dags/orders_etl_dag.py`）の
両方で実装した。ここでは2つのツールの設計思想とコードの違いを整理する。

---

## 1. 概要比較

| 項目 | Prefect | Airflow |
|---|---|---|
| 初回リリース | 2018 年 | 2014 年（Airbnb 発祥） |
| 書き方 | 普通の Python 関数に `@flow` / `@task` を付けるだけ | DAG（有向非巡回グラフ）を明示的に定義する |
| 学習コスト | 低い | 中〜高い |
| 求人市場 | 増加中 | 圧倒的多数 |
| スケジュール | Deployment + Work Pool | スケジューラーが DAG ファイルを監視 |
| UI | シンプル、モダン | 機能豊富、情報量が多い |

---

## 2. コード比較

### フロー / DAG の定義

**Prefect**
```python
from prefect import flow, task

@flow(name="orders-etl-pipeline")
def etl_pipeline():
    setup_schema_task(engine)
    last_loaded = get_watermark_task(engine)
    ...
```

**Airflow**
```python
from airflow.decorators import dag, task

@dag(dag_id="orders_etl", schedule="@daily", catchup=False)
def orders_etl_dag():
    schema_done = setup_schema()
    last_loaded = get_watermark_task()
    schema_done >> last_loaded  # 依存関係を明示
    ...
```

最大の違い: Airflow では **タスクの依存関係（誰が誰の後に動くか）を `>>` で明示する**。
Prefect は引数として渡すことで自動的に依存関係が決まる。

---

### タスク間のデータ受け渡し

**Prefect**
```python
@task
def extract(since):
    df = read_orders_csv(since=since)
    return df  # DataFrame をそのまま返せる

@task
def validate(df):
    return validate_orders(df)  # DataFrame をそのまま受け取れる
```

**Airflow**
```python
@task
def extract(since_str):
    df = read_orders_csv(since=since)
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")  # JSON に変換して XCom 経由で渡す

@task
def validate(records: list[dict]):
    df = pd.DataFrame(records)           # dict から DataFrame に戻す
    df["order_date"] = pd.to_datetime(df["order_date"])
    ...
```

Airflow はタスク間のデータを **XCom**（クロスコミュニケーション）という仕組みで渡す。
XCom は DB に保存されるため **JSON にシリアライズできるデータしか渡せない**。
DataFrame は直接渡せないため、dict のリストに変換する必要がある。

> **XCom のサイズ制限**: デフォルトで 48KB（PostgreSQL バックエンドでは制限緩和可能）。
> 大量データを渡す場合は S3 や GCS に書き出して「ファイルパス」だけを XCom で渡すのが本番での定石。

---

### リトライ設定

**Prefect**
```python
@task(retries=3, retry_delay_seconds=10)
def load_staging_task(df, engine):
    ...
```

**Airflow**
```python
@task(task_id="load_staging", retries=3, retry_delay=timedelta(seconds=10))
def load_staging(records):
    ...
# または DAG レベルで default_args に設定する
default_args = {"retries": 2, "retry_delay": timedelta(seconds=5)}
```

---

### 失敗時通知

**Prefect**
```python
def on_flow_failure(flow, flow_run, state):
    notifier.send(title=..., message=state.message)

@flow(on_failure=[on_flow_failure])
def etl_pipeline():
    ...
```

**Airflow**
```python
def notify_on_failure(context: dict):
    dag_id = context["dag"].dag_id
    task_id = context["task_instance"].task_id
    exception = context.get("exception")
    notifier.send(title=f"失敗: {dag_id}/{task_id}", message=str(exception))

@dag(default_args={"on_failure_callback": notify_on_failure})
def orders_etl_dag():
    ...
```

Airflow は `context` 辞書で DAG・タスク・例外の情報を受け取る。
Prefect は `flow`, `flow_run`, `state` の3引数で受け取る。

---

## 3. 依存関係の定義方法

Airflow には2種類の依存関係定義がある。

### ① `>>` 演算子（明示的な順序制約）

```python
schema_done >> last_loaded   # schema_done が終わってから last_loaded を実行
staging_done >> dwh_done     # staging が終わってから DWH ロード
```

### ② 引数渡し（XCom による自動依存）

```python
records = extract(last_loaded)   # extract は last_loaded の結果を使う
validated = validate(records)    # validate は extract の結果を使う
```

引数として渡すと、Airflow が「この値は前のタスクの出力だ」と判断し、
自動的に依存関係を設定する（TaskFlow API の特徴）。

---

## 4. スケジュール設定

**Prefect**（Deployment を使う）
```bash
prefect deploy pipeline.py:etl_pipeline \
  --name daily-etl \
  --cron "0 0 * * *"
```

**Airflow**（DAG 定義に書く）
```python
@dag(schedule="@daily", catchup=False)
def orders_etl_dag():
    ...
```

Airflow は DAG ファイルにスケジュールを直接書く。
Prefect は Deployment という別概念でスケジュールを管理する。

---

## 5. どちらを使うべきか

| 状況 | 推奨 |
|---|---|
| 既存の Airflow 環境がある | Airflow |
| 新規プロジェクト・Python ネイティブに書きたい | Prefect |
| チームに Airflow 経験者がいる | Airflow |
| 大規模データパイプライン（多数の DAG） | Airflow（実績が多い） |
| 手軽に始めたい・学習コストを下げたい | Prefect |

**結論**: 市場シェアは Airflow が圧倒的。ただし Prefect の方が「Python らしく書ける」ため
新規プロジェクトでは採用例が増えている。両方の概念を知っておくと転用しやすい。
