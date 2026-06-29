# STEP 6 - Prefect でジョブ化

## 目的

これまで `main.py` に直書きだった ETL を Prefect の `@flow` / `@task` でラップする。
これにより、実行履歴・ログ・リトライ・スケジュールを Prefect UI から管理できるようになる。

---

## やったこと

### 作成・変更したファイル

| ファイル | 内容 |
|---|---|
| `pipeline.py` | 新規作成。`@task` でステップを分割し、`@flow` でパイプライン全体を定義。各タスクにリトライ設定を追加。 |
| `tests/test_pipeline.py` | 新規作成。各タスクとフロー全体をモックでテスト（11件）。 |

### タスク構成

| タスク名 | 対応する関数 | リトライ |
|---|---|---|
| `setup-schema` | `create_table` + `create_watermark_table` + `create_dwh_tables` | 2回 |
| `get-watermark` | `get_watermark` | 2回 |
| `extract` | `read_orders_csv` | なし |
| `validate` | `validate_orders` | なし |
| `load-staging` | `upsert_orders` | 3回 |
| `load-dwh` | `upsert_dim_*` + `upsert_fact_orders` | 3回 |
| `update-watermark` | `update_watermark` | 2回 |

### ローカル UI での確認手順

```bash
# ターミナル1: Prefect サーバーを起動
.venv/bin/prefect server start

# ターミナル2: パイプラインを実行
PREFECT_API_URL=http://127.0.0.1:4200/api .venv/bin/python pipeline.py
```

ブラウザで `http://localhost:4200` を開くと以下が確認できる:
- **Flow Runs**: フローの実行一覧・成功/失敗状態
- **Task Runs**: 各タスクの所要時間・ログ
- **Deployments**: スケジュール設定（STEP 8 で追加予定）

---

## 学んだ概念

### @task と @flow

```python
@task(name="extract", retries=3, retry_delay_seconds=10)
def extract_task(csv_path, since):
    ...   # ← 個別の処理ステップ。失敗すると自動でリトライされる

@flow(name="orders-etl-pipeline")
def etl_pipeline():
    df = extract_task(...)   # ← タスクを順番に呼ぶのがフロー
    df = validate_task(df)
    ...
```

- **@task** — 実行ログ・状態（Completed / Failed）が記録される最小単位
- **@flow** — タスクをまとめてオーケストレーションする単位。UI から管理できる

### リトライ（retries / retry_delay_seconds）

```python
@task(retries=3, retry_delay_seconds=10)
def load_staging_task(...):
    ...
```

DB 接続が一時的に切れた場合など、一過性の失敗を自動で再試行できる。
`retry_delay_seconds=10` で再試行間隔を指定する。

### cache_policy=NO_CACHE

Prefect はタスクの引数をデフォルトでシリアライズしてキャッシュキーを計算しようとするが、
SQLAlchemy の `Engine` オブジェクトはシリアライズできないため警告が出る。
`cache_policy=NO_CACHE` を指定することで不要なキャッシュ処理を無効化できる。

```python
@task(cache_policy=NO_CACHE)
def my_task(engine):
    ...
```

### テスト時の @task/@flow の挙動

Prefect のタスク・フローは、テスト時に**通常の Python 関数として直接呼び出せる**。
そのため `unittest.mock` のモックをそのまま使えて、DB に接続せずにロジックだけをテストできる。

```python
def test_extract_task():
    with patch("pipeline.read_orders_csv", return_value=df):
        result = extract_task("path.csv", since=None)  # @task のまま呼べる
    assert isinstance(result, pd.DataFrame)
```

---

## 次のステップでの改善点

- 現状はコマンドラインから手動実行するだけ。STEP 8 で Docker Compose に Prefect サーバーを組み込み、
  スケジュール（Deployment）を設定して定期自動実行できるようにする。
- `pipeline.py` の `get_engine()` はタスクに渡すたびに呼んでいる。
  エンジンをフロー全体で共有する設計にすることでリソース効率が上がる。
