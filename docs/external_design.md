# 外部設計書

## 1. システム概要

### 1-1. 目的

ECサイトで発生した注文データ（CSV）を定期的に取り込み、分析用 DWH（データウェアハウス）へ格納する **ETL バッチパイプライン**。

### 1-2. 処理の全体像

```
┌─────────────────────────────────────────────────────────────────┐
│                         バッチ処理                               │
│                                                                 │
│  CSV ファイル                                                    │
│  (data/orders.csv)                                              │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────┐    ┌──────────┐    ┌────────────────────────┐    │
│  │ Extract  │───▶│Transform │───▶│         Load           │    │
│  │ CSV 読込 │    │ 検証・正規│    │ Staging → DWH          │    │
│  │ 増分抽出 │    │  化・集計 │    │ Upsert（べき等）        │    │
│  └──────────┘    └──────────┘    └────────────────────────┘    │
│                                            │                    │
│                                            ▼                    │
│                                    PostgreSQL (batch_db)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         ↕ 監視・通知
    Slack / 構造化ログ
```

### 1-3. システム構成

```
┌──────────────────────────────────────────────────────┐
│  Docker Compose（batch_network）                      │
│                                                      │
│  ┌──────────────────┐    ┌──────────────────┐        │
│  │  batch_postgres  │    │ batch_prefect_   │        │
│  │  PostgreSQL 16   │    │    server        │        │
│  │  port: 5432      │    │  Prefect UI/API  │        │
│  └────────┬─────────┘    │  port: 4200      │        │
│           │              └────────┬─────────┘        │
│           │                       │                  │
│           └──────┬────────────────┘                  │
│                  ▼                                   │
│        ┌──────────────────┐                          │
│        │ batch_prefect_   │                          │
│        │    worker        │                          │
│        │  pipeline.py     │                          │
│        └──────────────────┘                          │
└──────────────────────────────────────────────────────┘
```

| コンポーネント | 役割 | 使用技術 |
|---|---|---|
| batch_postgres | ETL データの永続化 | PostgreSQL 16 |
| batch_prefect_server | ジョブの管理・スケジュール・UI | Prefect 3 |
| batch_prefect_worker | ETL 処理の実行 | Python 3.12 / pandas / Prefect 3 |

---

## 2. 処理フロー

### 2-1. ETL パイプライン全体フロー

```
開始
  │
  ▼
① スキーマ準備
  ├── orders テーブルの作成（なければ）
  ├── watermarks テーブルの作成（なければ）
  └── dim / fact テーブルの作成（なければ）
  │
  ▼
② Watermark 取得
  ├── 初回 → None（全件モード）
  └── 2回目以降 → 前回最終取込日（増分モード）
  │
  ▼
③ Extract（CSV 読込）
  ├── 全件モード: CSV の全行を読み込む
  └── 増分モード: order_date > 前回最終取込日 の行だけ読み込む
  │
  ├── 新規データなし → スキップして終了
  │
  ▼
④ Validate（データ検証）
  ├── Pydantic: 行単位の型・値域チェック（エラー行は除外して継続）
  └── Pandera: DataFrame 全体の構造チェック（エラーがあれば例外）
  │
  ▼
⑤ Load Staging
  └── orders テーブルへ Upsert（order_id 単位）
  │
  ▼
⑥ Load DWH
  ├── dim_customer へ Upsert
  ├── dim_product へ Upsert
  ├── dim_date へ Upsert
  └── fact_orders へ Upsert
  │
  ▼
⑦ Watermark 更新
  └── 今回取り込んだ最大 order_date を記録
  │
  ▼
終了（成功）
```

### 2-2. 失敗時の動作

```
いずれかのタスクが失敗した場合
  │
  ├── Prefect が自動リトライ（タスクごとに設定）
  │     ├── setup-schema    : 最大 2 回リトライ（間隔 5 秒）
  │     ├── load-staging    : 最大 3 回リトライ（間隔 10 秒）
  │     ├── load-dwh        : 最大 3 回リトライ（間隔 10 秒）
  │     └── update-watermark: 最大 2 回リトライ（間隔 5 秒）
  │
  └── リトライ上限を超えた場合 → on_flow_failure フックが実行される
        └── Notifier が通知を送信
              ├── SLACK_WEBHOOK_URL が設定されている場合 → Slack に通知
              └── 未設定の場合 → 構造化 JSON をログ出力（stderr）
```

---

## 3. 入力インターフェース仕様

### 3-1. 入力ファイル

| 項目 | 内容 |
|---|---|
| ファイル形式 | CSV（UTF-8、BOM なし） |
| ファイルパス | `data/orders.csv`（デフォルト。引数で変更可） |
| ヘッダー行 | あり（1 行目） |
| 文字エンコーディング | UTF-8 |
| 日付フォーマット | `YYYY-MM-DD` |

### 3-2. CSV カラム仕様

| カラム名 | 型 | 必須 | 値域・形式 | 例 |
|---|---|:---:|---|---|
| order_id | 文字列 | ✓ | `ORD-` + 6桁数字。一意 | `ORD-000001` |
| customer_id | 文字列 | ✓ | `C-` + 4桁数字 | `C-0042` |
| customer_name | 文字列 | ✓ | 任意の文字列 | `田中太郎` |
| product_id | 文字列 | ✓ | `P001`〜`P005` のいずれか | `P003` |
| product_name | 文字列 | ✓ | 任意の文字列 | `モバイルバッテリー` |
| quantity | 整数 | ✓ | 1 以上 | `2` |
| unit_price | 整数 | ✓ | 1 以上（円） | `3980` |
| order_date | 日付 | ✓ | `YYYY-MM-DD` | `2024-03-15` |
| status | 文字列 | ✓ | `completed` / `pending` / `cancelled` | `completed` |

### 3-3. バリデーションルール

| チェック | ツール | エラー時の動作 |
|---|---|---|
| 型チェック（各カラム） | Pydantic | エラー行を除外して後続処理を続行 |
| quantity は 1 以上 | Pydantic | エラー行を除外して後続処理を続行 |
| unit_price は 1 以上 | Pydantic | エラー行を除外して後続処理を続行 |
| product_id が値域内 | Pydantic | エラー行を除外して後続処理を続行 |
| order_id の重複なし | Pandera | 例外を発生させてパイプラインを停止 |
| DataFrame の型・構造 | Pandera | 例外を発生させてパイプラインを停止 |

---

## 4. 出力インターフェース仕様

### 4-1. 出力先

| 出力先 | 内容 |
|---|---|
| PostgreSQL `orders` | ステージングデータ（生データを Upsert） |
| PostgreSQL `dim_customer` | 顧客マスター |
| PostgreSQL `dim_product` | 商品マスター |
| PostgreSQL `dim_date` | 日付マスター |
| PostgreSQL `fact_orders` | 注文ファクトデータ（DWH の中心） |
| stdout / Slack | 実行ログ・アラート通知 |

### 4-2. Upsert の動作（べき等性）

同一データを何度実行しても結果が変わらない **べき等** な設計。

| テーブル | 重複キー | 重複時の動作 |
|---|---|---|
| orders | order_id | 全カラムを上書き |
| dim_customer | customer_id | customer_name を上書き |
| dim_product | product_id | product_name / unit_price を上書き |
| dim_date | date_id | 何もしない（DO NOTHING） |
| fact_orders | order_id | 全カラムを上書き |

### 4-3. ログ出力フォーマット

正常時はプレーンテキスト、通知（アラート）は構造化 JSON で出力する。

```json
{
  "timestamp": "2024-03-15T10:30:00.123456+00:00",
  "level": "ERROR",
  "title": "ETL 失敗: orders-etl-pipeline",
  "message": "Flow Run: orders-etl-pipeline/run-abc123\n状態: ..."
}
```

---

## 5. 外部インターフェース

### 5-1. Prefect UI

| 項目 | 内容 |
|---|---|
| URL | `http://localhost:4200` |
| 機能 | フロー実行履歴・ログ閲覧・スケジュール設定・手動トリガー |

### 5-2. Slack 通知（オプション）

| 項目 | 内容 |
|---|---|
| 設定方法 | 環境変数 `SLACK_WEBHOOK_URL` に Webhook URL を設定する |
| 通知タイミング | フローが失敗したとき（`on_failure` フック） |
| 通知内容 | フロー名・実行名・エラー状態 |
| 未設定時 | stderr に JSON ログを出力（動作は継続） |

---

## 6. 実行方法

### 6-1. ローカル実行

```bash
# 仮想環境を有効化し、Prefect フローを直接実行
.venv/bin/python pipeline.py
```

### 6-2. Docker Compose 実行

```bash
# コンテナを起動
docker compose up -d

# ワーカーコンテナで ETL を手動実行
docker compose exec prefect-worker python pipeline.py

# Prefect UI でスケジュール・実行履歴を確認
# ブラウザで http://localhost:4200 を開く
```

### 6-3. Airflow 実行（発展）

```bash
# Airflow コンテナを起動（batch_network が起動済みであること）
docker compose -f docker-compose.airflow.yml up -d

# Airflow UI でスケジュール・実行履歴を確認
# ブラウザで http://localhost:8080 を開く（admin / admin）
```

---

## 7. エラーコード・対処一覧

| エラー | 原因 | 対処 |
|---|---|---|
| `SchemaErrors`（Pandera） | CSV の構造が仕様と一致しない | CSV ファイルの形式を確認する |
| `OperationalError`（SQLAlchemy） | DB 接続失敗 | PostgreSQL コンテナの起動状態を確認する |
| `FileNotFoundError` | CSV ファイルが存在しない | `data/` ディレクトリと CSV ファイルを確認する |
| Slack 通知失敗 | Webhook URL が無効 | `SLACK_WEBHOOK_URL` の値を確認する |
| リトライ上限超過 | 一時的な DB 負荷・ネットワーク障害 | Prefect UI でログを確認し、原因を特定して再実行する |
