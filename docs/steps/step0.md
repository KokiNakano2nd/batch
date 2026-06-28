# STEP 0 - 環境準備

## 目的
Python ETL バッチ処理を開発するための土台を整える。

## やったこと

### 1. pip / venv のインストール
Ubuntu 24.04 では Python 3.12 がプリインストールされているが、`pip` と `venv` は別途インストールが必要。

```bash
sudo apt-get install -y python3-pip python3-venv
```

### 2. Python 仮想環境の作成・有効化
プロジェクト専用の Python 環境を作ることで、他のプロジェクトとパッケージが混ざらないようにする。

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> **なぜ venv を使うのか？**
> システム全体に pip install すると、複数プロジェクトで依存関係が衝突する。
> `.venv` を作ることで「このプロジェクト専用の Python 環境」が手に入る。

### 3. Git 初期化
```bash
git init
git add .
git commit -m "STEP 0: 環境準備完了"
```

`.gitignore` に以下を追加：
- `.venv/` — 仮想環境（再現可能なので管理不要）
- `__pycache__/` — Python のキャッシュファイル
- `.env` — 接続情報などの秘匿情報
- `postgres_data/` — Docker ボリュームデータ

### 4. Docker で PostgreSQL を起動
本番に近い環境を最初から使うため、SQLite ではなく PostgreSQL を採用。

`docker-compose.yml` を作成：

```yaml
services:
  postgres:
    image: postgres:16
    container_name: batch_postgres
    environment:
      POSTGRES_USER: batch_user
      POSTGRES_PASSWORD: batch_pass
      POSTGRES_DB: batch_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

```bash
docker compose up -d
```

### 5. プロジェクトディレクトリ構成

```
Batch/
├── data/           # 入力 CSV・生成スクリプト
├── src/
│   ├── extract/    # CSV 読み込みロジック
│   ├── transform/  # 変換・検証ロジック（STEP 2 以降）
│   └── load/       # DB 書き込みロジック
├── tests/          # テスト（STEP 3 以降）
├── docs/steps/     # 各 STEP の説明ドキュメント
├── docker-compose.yml
├── PLAN.md
└── main.py
```

## 学んだ概念

| 概念 | 説明 |
|---|---|
| 仮想環境 (venv) | プロジェクト専用の Python 環境。パッケージの衝突を防ぐ |
| Docker Compose | 複数コンテナをまとめて定義・起動するツール |
| `.gitignore` | Git 管理から除外するファイル・ディレクトリを指定 |
