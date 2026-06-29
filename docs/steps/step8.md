# STEP 8 - Docker Compose 完成形

## 目的

これまでホスト上で手動実行していた ETL と Prefect サーバーを Docker Compose で統合する。
`docker compose up -d` 1コマンドで PostgreSQL + Prefect サーバー + Worker が揃った
本番に近い環境が再現できるようにする。

---

## やったこと

### 作成・変更したファイル

| ファイル | 内容 |
|---|---|
| `requirements.txt` | 新規作成。Worker イメージのビルドに使用するパッケージ一覧。 |
| `Dockerfile` | 新規作成。Worker コンテナ用イメージ定義。 |
| `docker-compose.yml` | `prefect-server` / `prefect-worker` サービスを追加。healthcheck も設定。 |
| `src/load/writer.py` | `DB_URL` を環境変数 `DATABASE_URL` から読むよう修正。 |

### コンテナ構成

```
[ブラウザ] :4200
      ↓
[prefect-server]  prefecthq/prefect:3-latest
      ↑  PREFECT_API_URL
[prefect-worker]  ./Dockerfile（Python 3.12 + requirements.txt）
      ↓  DATABASE_URL
[postgres]        postgres:16
```

### 起動・実行コマンド

```bash
# 全コンテナをバックグラウンドで起動
docker compose up -d

# ETL を1回手動実行
docker compose run --rm prefect-worker python pipeline.py

# ログを確認
docker compose logs prefect-server
docker compose logs -f prefect-worker  # -f でリアルタイム追跡

# 全コンテナを停止・削除
docker compose down
```

---

## 学んだ概念

### healthcheck

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U batch_user -d batch_db"]
  interval: 5s
  timeout: 5s
  retries: 5
```

コンテナが「起動した」だけでなく「サービスとして使える状態」かをチェックする仕組み。
`depends_on: condition: service_healthy` と組み合わせることで、
PostgreSQL が本当に受付可能になってから Worker が起動するよう順序制御できる。

### 環境変数による設定の外部化

```python
# src/load/writer.py
DB_URL = os.environ.get("DATABASE_URL", "postgresql://...@localhost:5432/batch_db")
```

- ローカル開発時: 環境変数なし → デフォルト値（localhost）を使用
- Docker Compose: `DATABASE_URL=postgresql://...@postgres:5432/batch_db` を注入

コードを変えずに接続先を切り替えられる。12-Factor App の原則のひとつ。

### docker compose run vs exec

| コマンド | 用途 |
|---|---|
| `docker compose run --rm サービス名 コマンド` | 新しいコンテナを1回起動して実行後に削除 |
| `docker compose exec サービス名 コマンド` | 起動中のコンテナの中でコマンドを実行 |

Worker は常駐プロセスを持たないため `run` を使う。
`--rm` を付けることで実行後にコンテナが自動削除される。

### SLACK_WEBHOOK_URL の渡し方

```yaml
# docker-compose.yml
environment:
  SLACK_WEBHOOK_URL: ${SLACK_WEBHOOK_URL:-}
```

```bash
# ホスト側で設定するだけで Worker コンテナに自動で渡る
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
docker compose up -d
```

`${変数名:-}` は「なければ空文字」の意味。未設定でもエラーにならない。

---

## 次のステップでの改善点

- 現在は `docker compose run` で手動実行している。STEP 9 で Prefect の Deployment を設定し、
  `prefect deploy` + Work Pool でスケジュール自動実行できるようにする。
- Prefect サーバーのデータは Docker Volume（SQLite）に保存されているが、
  本番では Prefect Cloud（SaaS）を使うと管理が不要になる。
- `Dockerfile` は現在シンプルな構成。本番ではマルチステージビルドでイメージサイズを削減できる。
