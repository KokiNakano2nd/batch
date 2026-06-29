# インフラ構成図

## 1. 全体構成

本システムは Docker Compose で管理される 2 つのスタックで構成される。

| スタック | ファイル | 用途 |
|---|---|---|
| ETL スタック | `docker-compose.yml` | PostgreSQL + Prefect（通常運用） |
| Airflow スタック | `docker-compose.airflow.yml` | Airflow（発展・学習用） |

2 つのスタックは `batch_network` という名前付きネットワークで接続されており、  
Airflow コンテナから ETL 用 PostgreSQL（`batch_postgres`）へアクセスできる。

---

## 2. ETL スタック（docker-compose.yml）

```
┌─────────────────────────────── batch_network ──────────────────────────────┐
│                                                                             │
│  ┌───────────────────────┐        ┌───────────────────────┐                │
│  │   batch_postgres      │        │  batch_prefect_server │                │
│  │   postgres:16         │        │  prefecthq/prefect:3  │                │
│  │                       │        │                       │                │
│  │  DB: batch_db         │        │  UI / API サーバー     │                │
│  │  User: batch_user     │        │  port: 4200           │                │
│  │  port: 5432           │        │                       │                │
│  │                       │        │  Volume:              │                │
│  │  Volume:              │        │  prefect_data         │                │
│  │  postgres_data        │        │  (SQLite メタDB)      │                │
│  └──────────┬────────────┘        └──────────┬────────────┘                │
│             │ healthcheck OK                  │ healthcheck OK              │
│             └──────────────┬─────────────────┘                             │
│                            │ depends_on (両方の起動を待つ)                   │
│                            ▼                                               │
│              ┌─────────────────────────┐                                   │
│              │  batch_prefect_worker   │                                   │
│              │  Dockerfile (自前ビルド) │                                   │
│              │  python:3.12-slim       │                                   │
│              │                         │                                   │
│              │  pipeline.py を実行     │                                   │
│              │                         │                                   │
│              │  ENV:                   │                                   │
│              │  DATABASE_URL=          │                                   │
│              │    postgres:5432/...    │                                   │
│              │  PREFECT_API_URL=       │                                   │
│              │    prefect-server:4200  │                                   │
│              │  SLACK_WEBHOOK_URL=     │                                   │
│              │    (任意)               │                                   │
│              │                         │                                   │
│              │  Volume:                │                                   │
│              │  ./data → /app/data     │                                   │
│              └─────────────────────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

ホストマシン（localhost）
  ├── :5432  →  batch_postgres
  └── :4200  →  batch_prefect_server（Prefect UI）
```

### コンテナ詳細

| コンテナ名 | イメージ | ポート | 役割 |
|---|---|---|---|
| `batch_postgres` | `postgres:16` | 5432 | ETL データの永続化 |
| `batch_prefect_server` | `prefecthq/prefect:3-latest` | 4200 | ジョブ管理 UI / API |
| `batch_prefect_worker` | Dockerfile（自前ビルド） | なし | ETL 処理の実行 |

### ヘルスチェック設定

| コンテナ | チェック内容 | 間隔 | 最大リトライ |
|---|---|---|---|
| `batch_postgres` | `pg_isready -U batch_user -d batch_db` | 5 秒 | 5 回 |
| `batch_prefect_server` | `/api/health` エンドポイントへ HTTP GET | 10 秒 | 10 回 |

`batch_prefect_worker` は両コンテナの healthcheck が OK になるまで起動しない（`depends_on: condition: service_healthy`）。

---

## 3. Airflow スタック（docker-compose.airflow.yml）

```
┌─── airflow_internal ───────────────────────────────────────┐
│                                                            │
│  ┌─────────────────────┐                                   │
│  │   airflow_postgres  │  ← Airflow のメタデータ専用        │
│  │   postgres:16       │     （ETL データとは別の DB）       │
│  │   DB: airflow       │                                   │
│  └──────────┬──────────┘                                   │
│             │ healthcheck OK                               │
│             ▼                                              │
│  ┌─────────────────────┐                                   │
│  │    airflow_init     │  ← 起動時 1 回のみ実行             │
│  │    airflow db       │     DB マイグレーション +           │
│  │    migrate          │     admin ユーザー作成             │
│  └─────────────────────┘                                   │
│                                                            │
│  ┌─────────────────────┐   ┌─────────────────────┐        │
│  │  airflow_webserver  │   │  airflow_scheduler  │        │
│  │  port: 8080         │   │                     │        │
│  │  (Web UI)           │   │  DAG の監視・         │        │
│  │                     │   │  タスクのキュー投入   │        │
│  └─────────────────────┘   └─────────────────────┘        │
│                                                            │
└────────────────────────────────────────────────────────────┘
         │ batch_network (external)
         ▼
┌─────────────────────────────── batch_network ─────────────┐
│                                                           │
│  ┌──────────────────────┐                                 │
│  │   batch_postgres     │  ← ETL データの読み書き          │
│  │   (STEP 8 で起動済み) │                                 │
│  └──────────────────────┘                                 │
│                                                           │
└───────────────────────────────────────────────────────────┘

ホストマシン（localhost）
  └── :8080  →  airflow_webserver（Airflow UI）
```

### コンテナ詳細

| コンテナ名 | イメージ | ポート | 役割 |
|---|---|---|---|
| `airflow_postgres` | `postgres:16` | なし（内部のみ） | Airflow メタデータの永続化 |
| `airflow_init` | `apache/airflow:2.10.0` | なし | DB 初期化（1 回のみ） |
| `airflow_webserver` | `apache/airflow:2.10.0` | 8080 | DAG 管理 UI |
| `airflow_scheduler` | `apache/airflow:2.10.0` | なし | DAG スケジューリング |

---

## 4. ネットワーク構成

```
┌─ batch_network（name: batch_network）────────────────────┐
│                                                          │
│  batch_postgres        ← ETL データの読み書き             │
│  batch_prefect_server  ← Prefect API へのアクセス         │
│  batch_prefect_worker  ← ETL 処理の実行                  │
│  airflow_webserver     ┐                                 │
│  airflow_scheduler     ┤ ← batch_postgres にアクセスする  │
│                        │   ために batch_network に参加    │
└────────────────────────┼─────────────────────────────────┘
                         │
┌─ airflow_internal ─────┼─────────────────────────────────┐
│                        │                                 │
│  airflow_postgres      │ ← Airflow メタDB（外部に非公開）  │
│  airflow_init          │                                 │
│  airflow_webserver     ┘                                 │
│  airflow_scheduler                                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

| ネットワーク名 | 種別 | 参加コンテナ | 用途 |
|---|---|---|---|
| `batch_network` | 名前付き（`docker-compose.yml` で作成） | ETL コンテナ + Airflow コンテナ | ETL DB への共有アクセス |
| `airflow_internal` | 内部（`docker-compose.airflow.yml` で作成） | Airflow コンテナのみ | Airflow 内部通信（メタDB など） |

---

## 5. ボリューム構成

| ボリューム名 | マウント先 | 用途 |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data`（batch_postgres） | ETL データの永続化 |
| `prefect_data` | `/root/.prefect`（batch_prefect_server） | Prefect メタデータ（SQLite） |
| `airflow_postgres_data` | `/var/lib/postgresql/data`（airflow_postgres） | Airflow メタデータの永続化 |
| `airflow_logs` | `/opt/airflow/logs`（Airflow コンテナ） | DAG タスクのログ |
| `./data`（バインドマウント） | `/app/data`（batch_prefect_worker） | CSV ファイルの共有 |
| `.`（バインドマウント・読取専用） | `/opt/airflow/project`（Airflow コンテナ） | ETL ソースコードの共有 |

---

## 6. 環境変数一覧

### batch_prefect_worker

| 変数名 | 値 | 説明 |
|---|---|---|
| `DATABASE_URL` | `postgresql://batch_user:batch_pass@postgres:5432/batch_db` | ETL DB 接続先（コンテナ名で解決） |
| `PREFECT_API_URL` | `http://prefect-server:4200/api` | Prefect API の接続先 |
| `SLACK_WEBHOOK_URL` | `${SLACK_WEBHOOK_URL:-}`（任意） | 未設定時は LogNotifier にフォールバック |

### Airflow コンテナ共通（x-airflow-common）

| 変数名 | 値 | 説明 |
|---|---|---|
| `AIRFLOW__CORE__EXECUTOR` | `LocalExecutor` | タスクをローカルプロセスで実行 |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | `postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow` | Airflow メタDB 接続先 |
| `DATABASE_URL` | `postgresql://batch_user:batch_pass@batch_postgres:5432/batch_db` | ETL DB 接続先（コンテナ名で解決） |
| `PYTHONPATH` | `/opt/airflow/project` | `src/` パッケージを import 可能にする |
| `_PIP_ADDITIONAL_REQUIREMENTS` | `pandas pandera pydantic pydantic-extra-types` | 起動時に追加インストールするパッケージ |

---

## 7. 起動手順

```bash
# --- ETL スタック（通常運用）---

# 起動
docker compose up -d

# 状態確認
docker compose ps

# Prefect UI
# http://localhost:4200

# ETL を手動実行
docker compose exec prefect-worker python pipeline.py

# 停止
docker compose down


# --- Airflow スタック（発展・学習用）---
# ※ ETL スタックを先に起動しておくこと（batch_network の作成が必要）

# 起動
docker compose -f docker-compose.airflow.yml up -d

# Airflow UI
# http://localhost:8080  (admin / admin)

# 停止
docker compose -f docker-compose.airflow.yml down
```
