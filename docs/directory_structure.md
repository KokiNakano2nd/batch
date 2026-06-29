# ディレクトリ構成

プロジェクトルート: `/home/test/Batch/`

```
Batch/
│
├── pipeline.py                  # Prefect フロー定義（@flow / @task）。ETL の全体制御とリトライ設定
├── main.py                      # スクリプト起動用エントリポイント（pipeline.py を直接呼ぶ場合）
├── requirements.txt             # Python パッケージ一覧
├── Dockerfile                   # ETL コンテナイメージのビルド定義
├── docker-compose.yml           # ETL スタック（ETL + Prefect サーバー + Prefect ワーカー + PostgreSQL）
├── docker-compose.airflow.yml   # Airflow スタック（Webserver + Scheduler + Worker + PostgreSQL）
│
├── src/                         # アプリケーションコア
│   ├── __init__.py
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── reader.py            # pandas で CSV を読み込む（メインパイプライン用）
│   │   └── reader_polars.py     # polars で CSV を読み込む（大規模データ向け代替）
│   ├── transform/
│   │   ├── __init__.py
│   │   ├── validator.py         # Pydantic（行レベル）+ Pandera（DataFrame レベル）の 2 層バリデーション
│   │   ├── aggregator.py        # pandas による月次売上集計
│   │   └── duckdb_aggregator.py # DuckDB で CSV を直接 SQL 集計する代替実装
│   ├── load/
│   │   ├── __init__.py
│   │   ├── writer.py            # Staging テーブル（orders）への Upsert ロード
│   │   ├── dwh_loader.py        # DWH テーブル（dim_* / fact_orders）への Upsert ロード
│   │   └── watermark.py        # 増分抽出用ウォーターマーク（最終取込日時）の読み書き
│   └── notify/
│       ├── __init__.py
│       ├── base.py              # BaseNotifier 抽象クラス（send() インターフェース定義）
│       ├── factory.py           # get_notifier()：環境変数で LogNotifier / SlackNotifier を切り替え
│       ├── log_notifier.py      # JSON を stdout / stderr に出力する通知実装
│       └── slack_notifier.py    # Slack Incoming Webhook へ POST する通知実装
│
├── dags/
│   └── orders_etl_dag.py        # Airflow DAG 定義（@dag / @task）。pipeline.py の Airflow 移植版
│
├── tests/                       # pytest 単体テスト（17 件）
│   ├── __init__.py
│   ├── test_reader.py           # reader.py のテスト
│   ├── test_reader_polars.py    # reader_polars.py のテスト
│   ├── test_validator.py        # validator.py のテスト
│   ├── test_aggregator.py       # aggregator.py のテスト
│   ├── test_duckdb_aggregator.py# duckdb_aggregator.py のテスト
│   ├── test_writer.py           # writer.py のテスト
│   ├── test_dwh_loader.py       # dwh_loader.py のテスト
│   ├── test_watermark.py        # watermark.py のテスト
│   ├── test_notify.py           # notify/ のテスト
│   └── test_pipeline.py         # pipeline.py の統合テスト
│
├── data/
│   ├── generate.py              # Faker で受注データ（CSV）を生成するスクリプト
│   ├── orders.csv               # 生成済み受注データ（小規模）
│   └── orders_large.csv         # 生成済み受注データ（大規模：ベンチマーク用）
│
├── scripts/
│   ├── benchmark.py             # pandas / polars / DuckDB の読み込み速度比較（10 万件）
│   └── generate_large_data.py   # 大規模データ（100 万件規模）生成スクリプト
│
└── docs/                        # プロジェクトドキュメント
    ├── directory_structure.md   # 本ファイル：ディレクトリ構成の説明
    ├── db_design.md             # DB 設計書（6 テーブルの定義・ERD・データフロー）
    ├── external_design.md       # 外部設計書（システム概要・I/O 仕様・エラーコード表）
    ├── internal_design.md       # 内部設計書（モジュール設計・依存関係・エラーハンドリング方針）
    ├── infrastructure.md        # インフラ構成図（Docker Compose 2 スタック・ネットワーク・ボリューム）
    ├── prefect.md               # Prefect の概念と操作手順
    ├── airflow_vs_prefect.md    # Airflow と Prefect の設計思想の比較
    ├── adr/                     # Architecture Decision Records（技術選定の意思決定記録）
    │   ├── README.md            # ADR 一覧インデックス
    │   ├── 0001-data-processing-library.md  # pandas をメインに採用した理由
    │   ├── 0002-job-orchestration-tool.md   # Prefect + Airflow 両対応の理由
    │   ├── 0003-validation-two-layer.md     # Pydantic + Pandera の 2 層バリデーションの理由
    │   ├── 0004-upsert-idempotent-load.md   # Upsert によるべき等ロードの理由
    │   └── 0005-notifier-abstraction.md     # BaseNotifier 抽象化の理由
    └── steps/                   # 学習 STEP ごとの実装記録
        ├── step0.md             # STEP 0: 環境構築
        ├── step1.md             # STEP 1: 最小 ETL（Faker → pandas → PostgreSQL）
        ├── step2.md             # STEP 2: Pydantic / Pandera によるデータ検証
        ├── step3.md             # STEP 3: pytest による単体テスト
        ├── step4.md             # STEP 4: Upsert・DWH ロード・増分抽出
        ├── step5.md             # STEP 5: Prefect によるオーケストレーション
        ├── step6.md             # STEP 6: Docker コンテナ化
        ├── step7.md             # STEP 7: polars / DuckDB による高速化
        ├── step8.md             # STEP 8: 通知レイヤー（BaseNotifier）
        ├── step9a.md            # STEP 9a: Airflow 移植
        └── step9b.md            # STEP 9b: Airflow 移植（続き）
```

---

## レイヤー構成

```
pipeline.py（Prefect フロー）
    │
    ├── src/extract/     — データ取り込み（CSV 読み込み・増分抽出）
    ├── src/transform/   — データ変換・検証・集計
    ├── src/load/        — データベースへの書き込み（Staging / DWH / Watermark）
    └── src/notify/      — 通知（ログ / Slack）
```

## 関連ドキュメント

| 知りたいこと | 参照先 |
|---|---|
| テーブル定義・ERD | [db_design.md](db_design.md) |
| システム全体の I/O 仕様 | [external_design.md](external_design.md) |
| モジュール間の依存・設計方針 | [internal_design.md](internal_design.md) |
| Docker 構成・ネットワーク | [infrastructure.md](infrastructure.md) |
| 技術選定の理由 | [adr/README.md](adr/README.md) |
| 各 STEP の学習内容 | [steps/](steps/) |
