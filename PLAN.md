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
- [ ] Faker で架空注文データを生成
- [ ] pandas で CSV 読み込み
- [ ] PostgreSQL へ全件ロード

### STEP 2 - データ検証
- [ ] Pydantic でスキーマ定義・バリデーション
- [ ] Pandera で DataFrame の検証ルールを追加

### STEP 3 - テスト
- [ ] pytest のセットアップ
- [ ] Extract / Transform / Load それぞれの単体テスト作成

### STEP 4 - 増分抽出 ＋ べき等 Upsert
- [ ] watermark（最終取込日時）管理テーブルの作成
- [ ] 増分抽出ロジックの実装
- [ ] INSERT ON CONFLICT による Upsert の実装

### STEP 5 - ディメンショナルモデリング
- [ ] 星型スキーマ設計（fact テーブル・dim テーブル）
- [ ] テーブル分割・マイグレーション
- [ ] 集計クエリの実装

### STEP 6 - Prefect でジョブ化
- [ ] `@flow` / `@task` によるパイプラインのラップ
- [ ] ローカル UI でスケジュール・リトライ動作の確認

### STEP 7 - 監視・アラート
- [ ] 失敗時の通知設計（Slack / メールなど）
- [ ] ジョブログの構造化

### STEP 8 - Docker Compose 完成形
- [ ] Docker Compose に Prefect サーバーを追加
- [ ] PostgreSQL + Prefect の統合動作確認

### STEP 9 - 発展（任意）
- [ ] Apache Airflow への移植・設計思想の比較
- [ ] polars / DuckDB を使った大規模データのチャンク処理

---

## 進捗
| STEP | 状態 | 完了日 |
|------|------|--------|
| 0    | 完了 | 2026-06-28 |
| 1    | 未着手 | - |
| 2    | 未着手 | - |
| 3    | 未着手 | - |
| 4    | 未着手 | - |
| 5    | 未着手 | - |
| 6    | 未着手 | - |
| 7    | 未着手 | - |
| 8    | 未着手 | - |
| 9    | 未着手 | - |
