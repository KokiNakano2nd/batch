# 0002 - ジョブ管理ツールの選定

## ステータス

採用（2026-06-29）

---

## 背景と問題

ETL パイプラインをスケジュール実行・監視するためのジョブ管理ツールが必要。  
タスクの失敗検知・リトライ・実行履歴の確認を UI から行えるものが望ましい。

**判断が必要な問い：**  
どのジョブ管理ツールをメインに採用し、どう学習するか。

---

## 意思決定の基準

- Python コードと親和性が高く、`@decorator` でシームレスに統合できること
- ローカル環境（Docker）で完結できること
- 実行履歴・ログ・リトライが UI から確認できること
- 実務で採用実績があること

---

## 検討した選択肢

### A. Prefect をメインに採用し、Airflow も学習用に実装する（採用）

### B. Prefect のみ採用する

### C. Airflow のみ採用する

### D. cron + シェルスクリプト

---

## 決定

**A. Prefect をメインパイプラインに採用し、Airflow への移植も実装する。**

- `pipeline.py` — Prefect フロー（`@flow` / `@task`）
- `dags/orders_etl_dag.py` — Airflow DAG（`@dag` / `@task`）
- `docker-compose.yml` — Prefect サーバー + ワーカー
- `docker-compose.airflow.yml` — Airflow 環境

### 採用による良い点

- Prefect は Python コードへの侵襲が最小（`@flow` / `@task` を追加するだけ）
- Airflow も実装することで、2 つの設計思想の違いを実地で比較できる
- 両方習得することで、現場での技術選択に対応できる

### 採用による懸念点

- 2 つのツールを維持するコストが発生する
- Airflow の XCom 制約（DataFrame を `list[dict]` に変換する必要がある）など、移植コストが発生した

---

## 各選択肢の比較

### A. Prefect + Airflow（採用）

**良い点**
- 両方実装することで設計思想の違いを体感できる
- Prefect：Python コードと自然に統合できる
- Airflow：エンタープライズで最も普及しており、実務経験として価値が高い

**懸念点**
- Airflow は XCom 経由のデータ渡しに型制約がある（DataFrameを直接渡せない）
- セットアップコストが Prefect より高い

---

### B. Prefect のみ

**良い点**
- セットアップが最もシンプル
- Python コードへの変更が最小限
- リトライ・ログ・スケジュールを `@flow` / `@task` の引数で直感的に設定できる

**懸念点**
- Airflow の設計思想（DAG / XCom / Operator）を学ぶ機会がなくなる
- エンタープライズで Airflow が主流の環境への対応力が身につかない

---

### C. Airflow のみ

**良い点**
- エンタープライズで最も普及しているオーケストレーターのため、即戦力になる
- 豊富なオペレーター（PostgresOperator など）が標準提供されている

**懸念点**
- 既存 Python コードを「DAG + Task 関数」に大きく書き直す必要がある
- XCom による DataFrame 受け渡しに変換コストが生じる
- ローカル環境のセットアップが Prefect より複雑

---

### D. cron + シェルスクリプト

**良い点**
- 依存ライブラリなし。追加学習コストがゼロ

**懸念点**
- 失敗検知・リトライ・実行履歴の管理を自前で実装する必要がある
- UI がないため、運用時の可視性が低い

---

## ツール比較サマリー

| 観点 | Prefect | Airflow |
|---|---|---|
| Python 統合 | `@flow` / `@task` をそのまま付与 | DAG 構造に書き直しが必要 |
| データの受け渡し | 関数の戻り値をそのまま渡せる | XCom 経由（JSON シリアライズ制約あり） |
| 依存関係の表現 | 関数呼び出しの順序で自動解決 | `>>` 演算子で明示的に定義 |
| スケジュール | `@flow(schedules=...)` | `@dag(schedule=...)` |
| リトライ設定 | `@task(retries=N)` | `default_args={"retries": N}` |
| 失敗通知 | `@flow(on_failure=[hook])` | `on_failure_callback` |
| セットアップ難易度 | 低い | 高い（複数コンテナ必要） |

---

## 参考

- [Prefect ドキュメント](https://docs.prefect.io/)
- [Airflow ドキュメント](https://airflow.apache.org/docs/)
- プロジェクト内比較ドキュメント: `docs/airflow_vs_prefect.md`
