# Python ETL バッチ処理 学習計画

## テーマ
Python で「大量データの ETL 設計」を実装しながら学ぶ。
あわせてジョブ管理サーバ（Prefect → Airflow）の使い方も習得する。

## 題材
**ECサイトの注文データを取り込む ETL パイプライン**

```
受注データ(CSV/API) → Extract(増分抽出) → Transform(検証・正規化・集計) → Load(べき等Upsert) → DWH(星型スキーマ)
```

---

## 学習 STEP

### STEP 0 - 環境準備
- [x] pip の導入
- [x] Python 仮想環境の作成・有効化
- [x] Git 初期化・最初のコミット
- [x] Docker のインストール確認・PostgreSQL コンテナ起動
- [x] プロジェクトディレクトリ構成の作成

### STEP 1 - 最小 ETL（全件ロード）
- [x] Faker で架空注文データを生成
- [x] pandas で CSV 読み込み
- [x] PostgreSQL へ全件ロード

### STEP 2 - データ検証
- [x] Pydantic でスキーマ定義・バリデーション
- [x] Pandera で DataFrame の検証ルールを追加

### STEP 3 - テスト
- [x] pytest のセットアップ
- [x] Extract / Transform / Load それぞれの単体テスト作成

### STEP 4 - 増分抽出 ＋ べき等 Upsert
- [x] watermark（最終取込日時）管理テーブルの作成
- [x] 増分抽出ロジックの実装
- [x] INSERT ON CONFLICT による Upsert の実装

### STEP 5 - ディメンショナルモデリング
- [x] 星型スキーマ設計（fact テーブル・dim テーブル）
- [x] テーブル分割・マイグレーション
- [x] 集計クエリの実装

### STEP 6 - Prefect でジョブ化
- [x] `@flow` / `@task` によるパイプラインのラップ
- [x] ローカル UI でスケジュール・リトライ動作の確認

### STEP 7 - 監視・アラート
- [x] 失敗時の通知設計（Slack / メールなど）
- [x] ジョブログの構造化

### STEP 8 - Docker Compose 完成形
- [x] Docker Compose に Prefect サーバーを追加
- [x] PostgreSQL + Prefect の統合動作確認

### STEP 9 - 発展（任意）
- [x] Apache Airflow への移植・設計思想の比較
- [x] polars / DuckDB を使った大規模データのチャンク処理

---

## 進捗
| STEP | 状態 | 完了日 |
|------|------|--------|
| 0    | 完了 | 2026-06-28 |
| 1    | 完了 | 2026-06-28 |
| 2    | 完了 | 2026-06-28 |
| 3    | 完了 | 2026-06-28 |
| 4    | 完了 | 2026-06-29 |
| 5    | 完了 | 2026-06-29 |
| 6    | 完了 | 2026-06-29 |
| 7    | 完了 | 2026-06-29 |
| 8    | 完了 | 2026-06-29 |
| 9    | 完了 | 2026-06-29 |
