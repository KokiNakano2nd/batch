# Architecture Decision Records

このディレクトリはプロジェクトで行った技術的な意思決定を記録する。  
フォーマットは [MADR (Markdown Architectural Decision Records)](https://adr.github.io/madr/) を採用。

## 記録一覧

| No. | タイトル | ステータス | 決定日 |
|---|---|---|---|
| [0001](0001-data-processing-library.md) | データ処理ライブラリの選定 | 採用 | 2026-06-29 |
| [0002](0002-job-orchestration-tool.md) | ジョブ管理ツールの選定 | 採用 | 2026-06-29 |
| [0003](0003-validation-two-layer.md) | データ検証の 2 層アプローチ | 採用 | 2026-06-29 |
| [0004](0004-upsert-idempotent-load.md) | Upsert によるべき等ロードの採用 | 採用 | 2026-06-29 |
| [0005](0005-notifier-abstraction.md) | 通知レイヤーの抽象化 | 採用 | 2026-06-29 |

## ADR のステータス定義

| ステータス | 意味 |
|---|---|
| 提案 | 検討中。まだ確定していない |
| 採用 | 決定済み。現在の実装に反映されている |
| 廃止 | かつて採用されたが、現在は使われていない |
| 差し替え | 別の ADR に置き換えられた |
