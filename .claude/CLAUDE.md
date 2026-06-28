# プロジェクトルール

## 学習進捗管理

- 学習の進捗は `/home/test/Batch/PLAN.md` で管理する
- 各 STEP の完了時に `PLAN.md` のチェックボックスと進捗テーブルを更新する

## STEP ドキュメント作成ルール

- **各 STEP の実装が完了したら、必ず `docs/steps/stepN.md` を作成すること**
- ファイル名: `docs/steps/step0.md`, `docs/steps/step1.md`, ... と連番にする
- 記載内容（テンプレート）:
  1. **目的** — この STEP で何を達成するか
  2. **やったこと** — 作成・変更したファイルとその理由
  3. **学んだ概念** — 登場した技術用語・ライブラリの説明（初学者向け）
  4. **次のステップでの改善点** — 現状の何が課題で次に何を直すか

## コーディング方針

- 対象ユーザーは Python 初学者のため、コードの説明は丁寧に行う
- 実装は PLAN.md の STEP 順に進める（先行実装しない）
- パッケージは `.venv` 内にインストールする（`pip install` ではなく `.venv/bin/pip install`）

## 環境情報

- OS: Ubuntu 24.04 (WSL2)
- Python: `.venv/bin/python`（プロジェクトルート直下の仮想環境）
- DB: PostgreSQL 16（Docker コンテナ `batch_postgres`、ポート 5432）
- DB 接続: `postgresql://batch_user:batch_pass@localhost:5432/batch_db`
