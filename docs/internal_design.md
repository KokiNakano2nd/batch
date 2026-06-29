# 内部設計書

## 1. モジュール構成

```
Batch/
├── pipeline.py              # Prefect フロー定義・エントリーポイント
├── main.py                  # Prefect なしで直接実行するスクリプト
├── dags/
│   └── orders_etl_dag.py    # Airflow DAG 定義（発展）
├── src/
│   ├── extract/
│   │   ├── reader.py            # pandas 版 CSV 読込（増分抽出）
│   │   └── reader_polars.py     # polars 版 CSV 読込（大規模データ向け）
│   ├── transform/
│   │   ├── validator.py         # Pydantic + Pandera によるデータ検証
│   │   ├── aggregator.py        # DWH を使った SQL 集計（pandas 返却）
│   │   └── duckdb_aggregator.py # CSV を直接 SQL 集計（DuckDB 版）
│   ├── load/
│   │   ├── writer.py            # orders ステージングへの書き込み
│   │   ├── dwh_loader.py        # dim / fact テーブルへの書き込み
│   │   └── watermark.py         # 増分管理（最終取込日の読み書き）
│   └── notify/
│       ├── base.py              # 通知の抽象基底クラス
│       ├── factory.py           # 環境変数で通知先を切り替えるファクトリ
│       ├── log_notifier.py      # ログ出力（JSON）による通知実装
│       └── slack_notifier.py    # Slack Webhook による通知実装
└── scripts/
    ├── generate_large_data.py   # 10 万件のテストデータ生成
    └── benchmark.py             # pandas / polars / DuckDB の性能比較
```

---

## 2. レイヤー設計

モジュールは以下の 4 レイヤーに分かれ、**上位レイヤーのみが下位レイヤーを呼ぶ**。  
逆方向の依存（load → extract など）は存在しない。

```
┌──────────────────────────────────────────┐
│  pipeline.py / dags/orders_etl_dag.py    │  ← オーケストレーション層
│  （Prefect / Airflow のタスク定義）        │    各レイヤーを組み合わせる
└────────────────┬─────────────────────────┘
                 │ 呼び出す
     ┌───────────┼───────────────┐
     ▼           ▼               ▼
┌─────────┐ ┌──────────┐ ┌──────────┐
│ extract │ │transform │ │  load    │  ← 処理層
│  layer  │ │  layer   │ │  layer   │    純粋な処理のみ
└─────────┘ └──────────┘ └──────────┘
                                 │ 依存
                          ┌──────────┐
                          │  notify  │  ← 通知層
                          │  layer   │    失敗時のアラート
                          └──────────┘
```

---

## 3. モジュール詳細

### 3-1. extract レイヤー

#### `src/extract/reader.py`

| 関数 | 引数 | 戻り値 | 説明 |
|---|---|---|---|
| `read_orders_csv` | `file_path: str`<br>`since: date \| None` | `pd.DataFrame` | CSV を読み込む。`since` 指定時は増分抽出 |

**処理の流れ**
```
pd.read_csv(file_path, parse_dates=["order_date"])
    │
    └── since が None → 全件返す
    └── since あり  → order_date > since の行だけ返す
```

#### `src/extract/reader_polars.py`

| 関数 | 引数 | 戻り値 | 説明 |
|---|---|---|---|
| `read_orders_csv_polars` | `file_path: str`<br>`since: date \| None` | `pl.DataFrame` | polars の Lazy 評価で CSV を読み込む |

**pandas 版との違い**

| 観点 | pandas 版 | polars 版 |
|---|---|---|
| 読込方法 | `read_csv`（即時） | `scan_csv`（遅延）+ `collect()` |
| フィルタのタイミング | 全件読み込んでから絞り込む | 読み込みと同時に絞り込む |
| 速度（10 万件・増分） | 約 127 ms | 約 28 ms（約 4.6 倍速い） |
| 戻り値の型 | `pd.DataFrame` | `pl.DataFrame` |

---

### 3-2. transform レイヤー

#### `src/transform/validator.py`

**検証の 2 段階構成**

```
validate_orders(df)
    │
    ├── Step 1: validate_rows_with_pydantic(df)
    │       ├── 各行を OrderRow モデルに渡す
    │       ├── ValidationError → エラーをログ出力して行を除外（処理は続行）
    │       └── 正常行のみの DataFrame を返す
    │
    └── Step 2: validate_dataframe_with_pandera(df)
            ├── ORDER_SCHEMA.validate(df, lazy=True)
            ├── SchemaErrors → エラー詳細を出力して例外を再 raise（処理を停止）
            └── 検証済み DataFrame を返す
```

**OrderRow（Pydantic モデル）のフィールドと制約**

| フィールド | 型 | 制約 |
|---|---|---|
| order_id | `str` | なし |
| customer_id | `str` | なし |
| customer_name | `str` | なし |
| product_id | `str` | `P001`〜`P005` のいずれか |
| product_name | `str` | なし |
| quantity | `int` | 1 以上 |
| unit_price | `int` | 1 以上 |
| order_date | `date` | なし |
| status | `Literal["completed", "pending", "cancelled"]` | 3 値のいずれか |

**ORDER_SCHEMA（Pandera スキーマ）のチェック**

| カラム | 型 | チェック |
|---|---|---|
| order_id | `str` | なし（重複チェックは DataFrame 全体で実施） |
| quantity | `int` | `> 0` |
| unit_price | `int` | `> 0` |
| product_id | `str` | `isin({"P001"..."P005"})` |
| order_date | `datetime64[ns]` | nullable=False |
| （DataFrame 全体） | — | `order_id` の一意性チェック |

---

#### `src/transform/aggregator.py`

DWH（`fact_orders` + dim テーブル）に対して SQL で集計する。

| 関数 | 返却カラム | 説明 |
|---|---|---|
| `monthly_sales(engine)` | `year, month, total_amount, order_count` | 年月別売上合計・件数 |
| `product_sales_ranking(engine)` | `product_name, total_amount, total_quantity` | 商品別売上（降順） |
| `status_summary(engine)` | `status, order_count, total_amount` | ステータス別件数・金額 |

#### `src/transform/duckdb_aggregator.py`

CSV ファイルを直接 SQL でクエリする（DB 不要）。`aggregator.py` と同じ集計結果を返す。

| 関数 | 引数 | 説明 |
|---|---|---|
| `monthly_sales_duckdb(file_path)` | CSV パス | `read_csv_auto()` で月別集計 |
| `product_sales_ranking_duckdb(file_path)` | CSV パス | 商品別売上ランキング |
| `status_summary_duckdb(file_path)` | CSV パス | ステータス別集計 |

---

### 3-3. load レイヤー

#### `src/load/writer.py`

| 関数 | 説明 |
|---|---|
| `get_engine()` | `DATABASE_URL` 環境変数を使って SQLAlchemy Engine を生成する |
| `create_table(engine)` | `orders` テーブルを作成する（存在する場合はスキップ） |
| `load_orders(df, engine)` | 全件置換でロードする（STEP 1 の全件ロード用） |
| `upsert_orders(df, engine)` | `order_id` をキーに Upsert する（STEP 4 以降の通常運用） |

**DB 接続の切り替え仕組み**

```python
_DEFAULT_DB_URL = "postgresql://batch_user:batch_pass@localhost:5432/batch_db"
DB_URL = os.environ.get("DATABASE_URL", _DEFAULT_DB_URL)
```

| 実行環境 | DATABASE_URL の値 |
|---|---|
| ローカル（直接実行） | 未設定 → デフォルト値（localhost:5432）を使用 |
| Docker Compose | `postgres:5432`（コンテナ名でホスト解決） |
| Airflow コンテナ | `batch_postgres:5432`（外部ネットワーク経由） |

#### `src/load/watermark.py`

| 関数 | 説明 |
|---|---|
| `create_watermark_table(engine)` | `watermarks` テーブルを作成する |
| `get_watermark(engine, job_name)` | 最終取込日を取得する。未登録なら `None` |
| `update_watermark(engine, job_name, loaded_at)` | 最終取込日を Upsert する |

**増分抽出のシーケンス**

```
初回実行:
  get_watermark() → None
  extract(since=None) → 全件取込
  update_watermark(max_order_date)

2回目以降:
  get_watermark() → 2024-03-15（例）
  extract(since=2024-03-15) → 2024-03-16 以降のみ取込
  update_watermark(新しい max_order_date)
```

#### `src/load/dwh_loader.py`

| 関数 | 説明 |
|---|---|
| `create_dwh_tables(engine)` | dim / fact テーブルを全て作成する |
| `upsert_dim_customer(engine)` | `orders` → `dim_customer` へ Upsert |
| `upsert_dim_product(engine)` | `orders` → `dim_product` へ Upsert |
| `upsert_dim_date(engine)` | `orders` → `dim_date` へ Upsert |
| `upsert_fact_orders(engine)` | `orders` → `fact_orders` へ Upsert（`amount` を計算して格納） |

**トランザクション設計**

全ての書き込み処理で `engine.begin()` を使用する。

```python
with engine.begin() as conn:   # トランザクション開始
    conn.execute(text(sql))
# ブロックを抜けると自動コミット
# 例外が発生した場合は自動ロールバック
```

`engine.connect()` + `conn.commit()` を使わない理由: Airflow がバンドルする SQLAlchemy 1.4 では `conn.commit()` が存在しないため、両バージョンで動く `engine.begin()` に統一している。

---

### 3-4. notify レイヤー

**クラス図**

```
BaseNotifier（抽象クラス）
  │
  ├── LogNotifier     ← デフォルト。JSON を stdout/stderr に出力
  └── SlackNotifier   ← SLACK_WEBHOOK_URL 設定時に使用

get_notifier()        ← ファクトリ関数。環境変数で実装を切り替える
```

#### `src/notify/base.py`

```python
class BaseNotifier(ABC):
    @abstractmethod
    def send(self, title: str, message: str, level: str = "error") -> None: ...
```

新しい通知先を追加するときは `BaseNotifier` を継承して `send()` を実装するだけでよい。呼び出し側（`pipeline.py`）は変更不要。

#### `src/notify/log_notifier.py`

| level | 出力先 | logging レベル |
|---|---|---|
| `"error"` | stderr | `logger.error` |
| `"warning"` | stdout | `logger.warning` |
| `"info"` | stdout | `logger.info` |

出力フォーマット（JSON）:
```json
{"timestamp": "2024-03-15T10:30:00+00:00", "level": "ERROR", "title": "...", "message": "..."}
```

#### `src/notify/slack_notifier.py`

Slack Incoming Webhook へ POST する。`urllib.request` のみ使用（外部依存なし）。  
HTTP ステータスが 200 以外の場合は `RuntimeError` を raise する。

#### `src/notify/factory.py`

```python
def get_notifier() -> BaseNotifier:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if webhook_url:
        return SlackNotifier(webhook_url)
    return LogNotifier()
```

将来メール通知などを追加する場合、この関数に分岐を 1 行追加するだけでよい。

---

## 4. pipeline.py のタスク設計

### タスク一覧とリトライ設定

| タスク名 | 関数 | retries | retry_delay |
|---|---|:---:|---|
| setup-schema | `setup_schema_task` | 2 | 5 秒 |
| get-watermark | `get_watermark_task` | 2 | 5 秒 |
| extract | `extract_task` | 0（デフォルト） | — |
| validate | `validate_task` | 0（デフォルト） | — |
| load-staging | `load_staging_task` | 3 | 10 秒 |
| load-dwh | `load_dwh_task` | 3 | 10 秒 |
| update-watermark | `update_watermark_task` | 2 | 5 秒 |

extract / validate にリトライを設定しない理由: CSV 読込・バリデーションは冪等かつ副作用がないため、失敗した場合はデータ起因の問題であり、リトライしても解消しない。

### タスク実行順序

```
setup_schema_task
    ↓
get_watermark_task
    ↓
extract_task ─── 空なら return（スキップ）
    ↓
validate_task
    ↓
load_staging_task
    ↓
load_dwh_task
    ↓
update_watermark_task
```

---

## 5. エラーハンドリング方針

| 種別 | 対応方針 |
|---|---|
| Pydantic `ValidationError`（行レベル） | エラー行を除外してログ出力し、処理を続行する |
| Pandera `SchemaErrors`（DataFrame レベル） | 例外を raise してパイプラインを停止する |
| SQLAlchemy `OperationalError` | Prefect のリトライ機構に委ねる |
| リトライ上限超過 | `on_flow_failure` フックで通知を送信する |
| Slack 通知失敗（HTTP 非 200） | `RuntimeError` を raise する（通知失敗自体は握りつぶさない） |

---

## 6. テスト構成

```
tests/
├── test_reader.py           # extract/reader.py のテスト
├── test_reader_polars.py    # extract/reader_polars.py のテスト
├── test_validator.py        # transform/validator.py のテスト
├── test_writer.py           # load/writer.py のテスト
├── test_watermark.py        # load/watermark.py のテスト
├── test_dwh_loader.py       # load/dwh_loader.py のテスト
├── test_notify.py           # notify レイヤーのテスト
├── test_pipeline.py         # pipeline.py の統合テスト
└── test_duckdb_aggregator.py# transform/duckdb_aggregator.py のテスト
```

**モック戦略**

DB を使うテストはすべて `MagicMock` で SQLAlchemy Engine をモックする。実際の DB には接続しない。

```python
def _make_mock_engine():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    return mock_engine, mock_conn
```

`engine.begin()` を使っていることの確認は `mock_engine.begin.assert_called_once()` で行う。

**テスト実行コマンド**

```bash
.venv/bin/pytest tests/ -v
```
