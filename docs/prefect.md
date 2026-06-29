# Prefect ガイド

## 1. Prefect とは

### ひとことで言うと

**「データパイプラインをジョブとして管理するためのワークフローオーケストレーションツール」**

Python のコードに `@flow` / `@task` デコレータをつけるだけで、実行履歴の記録・失敗時のリトライ・スケジュール実行・ログ管理が使えるようになる。

---

### どんな問題を解決するのか

バッチ処理を素朴に書いた場合、次のような困りごとが起きる。

| 困りごと | 素朴な Python スクリプト | Prefect |
|---|---|---|
| 失敗したとき何が起きたか分からない | `print` を見に行く | UI でログと失敗箇所を確認できる |
| DB が一時的に落ちて失敗した | 手動で再実行 | `retries=3` で自動リトライ |
| 毎朝 6 時に実行したい | cron を手で設定 | Deployment でスケジュール管理 |
| どのステップが遅いか分からない | 計測コードを書く | UI で各タスクの所要時間を確認できる |
| 途中のステップから再実行したい | 難しい | タスク単位でリラン可能 |

---

### 似たツールとの比較

| ツール | 特徴 | 向いているケース |
|---|---|---|
| **cron** | OS のスケジューラ。管理機能なし | 単純な定期実行 |
| **Prefect** | Python ネイティブ。軽量で導入しやすい | 中規模のデータパイプライン |
| **Apache Airflow** | DAG を Python で書く。機能が豊富だが重い | 大規模・複雑なパイプライン |
| **Luigi** | タスク依存関係の管理が主目的 | バッチジョブの依存管理 |

このプロジェクトでは Prefect を選択。Airflow より導入コストが低く、Python コードへの変更も最小限で済むため。

---

## 2. 主要な概念

### Flow（フロー）

パイプライン全体を表す単位。`@flow` デコレータをつけた関数がフローになる。

```
@flow
def etl_pipeline():
    df = extract_task()
    df = validate_task(df)
    load_task(df)
```

- 複数のタスクをまとめてオーケストレーションする
- UI から実行履歴・ログ・状態を確認できる
- フロー内で別のフローを呼ぶこともできる（サブフロー）

---

### Task（タスク）

パイプラインの中の**個別の処理ステップ**。`@task` デコレータをつける。

```
@task
def extract_task(csv_path):
    return pd.read_csv(csv_path)
```

- 実行ログと状態（`Completed` / `Failed`）が記録される
- 失敗時のリトライ設定ができる
- タスクは必ずフローの中から呼ぶ

---

### Flow Run / Task Run（実行インスタンス）

フロー・タスクを実際に実行したときの「1回分の記録」。

```
Flow: etl_pipeline
  └─ Flow Run: "masked-skink"  ← 実行のたびにランダムな名前がつく
       ├─ Task Run: extract-230     (Completed, 0.1s)
       ├─ Task Run: validate-db8    (Completed, 0.5s)
       └─ Task Run: load-staging-6c4 (Completed, 0.3s)
```

Prefect UI の **Flow Runs** 画面で一覧できる。

---

### Deployment（デプロイメント）

フローを「いつ・どうやって実行するか」を設定したもの。

- cron スケジュール（例: 毎朝 6 時）
- 手動トリガー
- イベントトリガー（ファイルが来たら実行、など）

Deployment を作ると、コードを変更せずにスケジュールや実行設定を UI から変更できる。

---

### Worker / Work Pool（ワーカー）

実際にタスクを実行するプロセス。

```
Prefect サーバー（スケジュール管理・UI）
    ↓ 実行指示
Work Pool（実行環境のグループ）
    ↓
Worker（実際に Python を動かすプロセス）
```

ローカル開発では `python pipeline.py` で直接実行するため Worker を意識しなくてよい。
本番環境では Worker を常駐させてサーバーからの指示を待つ構成にする。

---

## 3. セットアップ

### インストール

```bash
.venv/bin/pip install "prefect>=3.0"
```

---

### Prefect サーバーの起動

```bash
.venv/bin/prefect server start
```

起動すると `http://localhost:4200` で UI にアクセスできる。
データ（実行履歴・ログ）はローカルの SQLite に保存される。

---

### ローカル実行とサーバーあり実行の違い

#### サーバーなし（デフォルト）

```bash
python pipeline.py
```

- Prefect が一時的なミニサーバーを自動で立てて実行する
- 終了後にサーバーも停止するため、UI で履歴を確認できない
- 開発中の動作確認に向いている

#### サーバーあり

```bash
# ターミナル1: サーバーを起動したままにする
.venv/bin/prefect server start

# ターミナル2: サーバーに接続して実行
PREFECT_API_URL=http://127.0.0.1:4200/api python pipeline.py
```

- 実行履歴・ログが UI に記録される
- 複数回実行した履歴を比較できる
- 本番運用や動作確認に向いている

---

## 4. @flow / @task の書き方

### 基本的な書き方

```python
from prefect import flow, task

@task
def add(a: int, b: int) -> int:
    return a + b

@flow
def my_pipeline():
    result = add(1, 2)
    print(result)  # 3

my_pipeline()  # フローを呼び出すと実行される
```

デコレータをつけるだけで、元のコードの動作は変わらない。

---

### 引数・戻り値の扱い

タスクの戻り値はそのまま次のタスクに渡せる。

```python
@task
def extract() -> pd.DataFrame:
    return pd.read_csv("data.csv")

@task
def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna()

@flow
def pipeline():
    df = extract()        # DataFrame が返る
    df = transform(df)    # そのまま渡せる
```

---

### よく使うオプション

#### @flow のオプション

```python
@flow(
    name="orders-etl-pipeline",   # UI に表示される名前
    log_prints=True,               # print() をログに記録する
)
def etl_pipeline():
    ...
```

#### @task のオプション

```python
@task(
    name="load-staging",          # UI に表示される名前
    retries=3,                     # 失敗時のリトライ回数
    retry_delay_seconds=10,        # リトライまでの待機秒数
    cache_policy=NO_CACHE,         # キャッシュを無効化
)
def load_staging_task(df, engine):
    ...
```

---

## 5. タスクの設定

### リトライ（retries / retry_delay_seconds）

一時的な障害（DB の接続切れ・API タイムアウトなど）に備えて、失敗したタスクを自動で再実行できる。

```python
@task(retries=3, retry_delay_seconds=10)
def load_task(df, engine):
    upsert_orders(df, engine)
```

上の例では、失敗した場合に最大 3 回・10 秒おきに再実行する。

```
1回目: 失敗 → 10秒待つ
2回目: 失敗 → 10秒待つ
3回目: 成功 → Completed
```

リトライをどこにつけるべきか：
- **DB 書き込み・読み込み** — 接続の一時的な切断に対応するため付ける
- **外部 API の呼び出し** — レートリミットやタイムアウトに対応するため付ける
- **純粋な計算処理（validate など）** — 同じ入力なら結果が変わらないため不要

---

### キャッシュ（cache_policy）

Prefect はデフォルトでタスクの引数をシリアライズ（変換）してキャッシュキーを作ろうとする。
しかし、SQLAlchemy の `Engine` オブジェクトはシリアライズできないため警告が出る。

```
HashError: Unable to create hash
  JSON error: Unable to serialize unknown type: <class 'sqlalchemy.engine.base.Engine'>
```

この場合は `cache_policy=NO_CACHE` でキャッシュを無効にする。

```python
from prefect.cache_policies import NO_CACHE

@task(cache_policy=NO_CACHE)
def setup_schema_task(engine):
    ...
```

---

### タスク名（name）

`name` を指定しないと関数名がそのまま UI に表示される。
日本語や分かりやすい名前をつけることで、UI での確認が楽になる。

```python
@task(name="load-staging")   # UI では "load-staging" と表示される
def load_staging_task(...):
    ...
```

---

## 6. ログと可観測性

### get_run_logger()

Prefect のロガーを使うと、ログが UI にも記録される。

```python
from prefect.logging import get_run_logger

@task
def extract_task(csv_path, since):
    logger = get_run_logger()
    df = read_orders_csv(csv_path, since=since)
    logger.info(f"{len(df)} 件を抽出しました。")  # UI のログに表示される
    return df
```

`print()` を使いたい場合は、フローに `log_prints=True` をつけると `print` もログに記録される。

```python
@flow(log_prints=True)
def etl_pipeline():
    print("ETL 開始")  # これも UI のログに記録される
```

---

### UI でのログ確認

1. `http://localhost:4200` にアクセス
2. **Flow Runs** → 見たいフランをクリック
3. **Logs** タブを開く

各タスクのログ・エラーメッセージ・実行時刻がまとめて確認できる。

```
12:55:55  INFO  Task run 'extract-230'  - 1000 件を抽出しました。
12:55:56  INFO  Task run 'validate-db8' - 検証完了: 1000 件が通過しました。
12:55:56  INFO  Task run 'load-staging' - ステージング: 1000 件をロードしました。
```

---

## 7. このプロジェクトでの実装（pipeline.py 解説）

### フロー全体の流れ

```
etl_pipeline()
  │
  ├─ setup_schema_task(engine)       # orders / watermarks / dim・fact テーブルを準備
  │
  ├─ get_watermark_task(engine)      # 前回の最終取込日を取得
  │       ↓ last_loaded（None or date）
  │
  ├─ extract_task(csv_path, last_loaded)   # 増分 CSV 読み込み
  │       ↓ df
  │
  │  ── df.empty なら終了 ──────────────────────────────
  │
  ├─ validate_task(df)               # Pydantic + Pandera で検証
  │       ↓ validated_df
  │
  ├─ load_staging_task(df, engine)   # orders テーブルへ Upsert
  │
  ├─ load_dwh_task(engine)           # dim → fact へ Upsert
  │
  └─ update_watermark_task(engine, new_watermark)   # 最終取込日を更新
```

---

### なぜ各ステップをタスクに分けたか

タスクを分けると、**どのステップで失敗したか** が UI で一目で分かる。

```
例: DB 接続が切れて load-staging が失敗した場合

✅ setup-schema    Completed
✅ get-watermark   Completed
✅ extract         Completed
✅ validate        Completed
❌ load-staging    Failed  ← ここで失敗したことが分かる
-  load-dwh        (実行されていない)
-  update-watermark (実行されていない)
```

分けなかった場合は「ETL 全体が失敗」としか分からず、ログを掘り起こす必要がある。

---

### cache_policy=NO_CACHE が必要だった理由

このプロジェクトでは `engine`（SQLAlchemy の接続オブジェクト）をタスクの引数に渡している。
Prefect はデフォルトで引数からキャッシュキーを計算しようとするが、`engine` はシリアライズできないため警告が出る。

該当するタスクすべてに `cache_policy=NO_CACHE` を指定することで解決した。

```python
# engine を引数に受け取るタスクはすべて NO_CACHE が必要
@task(cache_policy=NO_CACHE)
def setup_schema_task(engine): ...

@task(cache_policy=NO_CACHE)
def get_watermark_task(engine): ...

@task(cache_policy=NO_CACHE)
def load_staging_task(df, engine): ...

@task(cache_policy=NO_CACHE)
def load_dwh_task(engine): ...

@task(cache_policy=NO_CACHE)
def update_watermark_task(engine, new_watermark): ...
```

---

## 8. テストの書き方

### @task / @flow をテストで直接呼ぶ

Prefect のタスク・フローは、**テスト時に通常の Python 関数として直接呼び出せる**。
Prefect サーバーへの接続も不要で、`unittest.mock` のモックをそのまま使える。

```python
from unittest.mock import patch
import pandas as pd
from pipeline import extract_task

def test_extract_task_passes_since_to_reader():
    dummy_df = pd.DataFrame()
    since = date(2024, 6, 1)

    with patch("pipeline.read_orders_csv", return_value=dummy_df) as mock_read:
        extract_task("data/orders.csv", since=since)   # @task のまま呼べる
        mock_read.assert_called_once_with("data/orders.csv", since=since)
```

---

### フロー全体の結合テスト

フロー全体を一度に通すテストでは、DB 接続・CSV 読み込みをすべてモックに差し替える。

```python
def test_full_flow_runs_without_error():
    df = make_sample_df()

    with (
        patch("pipeline.get_engine", return_value=MagicMock()),
        patch("pipeline.create_table"),
        patch("pipeline.read_orders_csv", return_value=df),
        patch("pipeline.validate_orders", return_value=df),
        patch("pipeline.upsert_orders"),
        # ... その他のモック
    ):
        etl_pipeline()   # 例外が出なければ OK
```

---

### テスト実行時の警告について

タスクをフローの外で単独呼び出しすると、次の警告が出ることがある。

```
UserWarning: Logger 'prefect.task_runs' attempted to send logs to the API
without a flow run id.
```

これは「フロー実行コンテキストがないのでログを API に送れない」という通知で、テストの合否には影響しない。
気になる場合は環境変数で抑制できる。

```bash
PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW=ignore pytest
```

---

## 9. 次のステップ（Deployment・スケジュール）

### Deployment とは

フローを「いつ・どのように実行するか」の設定ファイル。

- コードを変えずに実行スケジュールを変更できる
- UI からワンクリックで手動実行もできる
- 複数の実行環境（ローカル・Docker・クラウド）を切り替えられる

---

### cron スケジュールで定期実行する方法

```python
from prefect.client.schemas.schedules import CronSchedule

# pipeline.py に追加
if __name__ == "__main__":
    etl_pipeline.serve(
        name="orders-etl-daily",
        cron="0 6 * * *",   # 毎朝 6 時に実行
    )
```

```bash
# サーバーを起動した状態で実行
PREFECT_API_URL=http://127.0.0.1:4200/api python pipeline.py
```

これで Prefect UI の **Deployments** 画面にスケジュールが登録され、毎朝 6 時に自動実行される。

---

### cron 記法の読み方

```
0 6 * * *
│ │ │ │ └─ 曜日（* = 毎日）
│ │ │ └─── 月（* = 毎月）
│ │ └───── 日（* = 毎日）
│ └─────── 時（6 = 6時）
└───────── 分（0 = 0分）
```

よく使うパターン：

| cron 式 | 意味 |
|---|---|
| `0 6 * * *` | 毎朝 6 時 |
| `0 0 * * 1` | 毎週月曜日の 0 時 |
| `0 * * * *` | 毎時 0 分 |
| `*/30 * * * *` | 30 分ごと |

---

### STEP 8 への橋渡し

STEP 8 では Prefect サーバー自体を Docker Compose に組み込む。
こうすることで「PC を再起動しても Prefect サーバーが自動で起動し、スケジュール実行が継続される」構成が完成する。

```yaml
# docker-compose.yml のイメージ（STEP 8 で実装）
services:
  postgres:
    image: postgres:16
    ...
  prefect-server:
    image: prefecthq/prefect:3-latest
    command: prefect server start
    ports:
      - "4200:4200"
```
