# 0004 - Upsert によるべき等ロードの採用

## ステータス

採用（2026-06-29）

---

## 背景と問題

ETL パイプラインはネットワーク障害・処理途中の失敗などにより、同じデータが複数回ロードされる可能性がある。  
また、ステータス変更（`pending` → `completed`）などのデータ更新にも対応する必要がある。

**判断が必要な問い：**  
重複実行・再実行時に安全なロード戦略をどう実装するか。

---

## 意思決定の基準

- 何度実行しても結果が変わらない（べき等性）こと
- 既存データの更新（ステータス変更など）に対応できること
- パイプライン失敗後の再実行が安全にできること

---

## 検討した選択肢

### A. INSERT ON CONFLICT DO UPDATE（Upsert）（採用）

### B. 全件 DELETE → INSERT（洗い替え）

### C. INSERT のみ（重複時はスキップ）

### D. pandas の `to_sql(if_exists="replace")`

---

## 決定

**A. `INSERT ON CONFLICT DO UPDATE` を使った Upsert を採用する。**

```sql
INSERT INTO orders (order_id, ...)
VALUES (:order_id, ...)
ON CONFLICT (order_id) DO UPDATE SET
    status = EXCLUDED.status,
    ...
```

- 新規データ → INSERT
- 既存データ（同一 `order_id`）→ 全カラムを上書き UPDATE

### 採用による良い点

- 何度実行しても同じ結果になる（べき等性）
- 失敗後の再実行が安全。途中失敗しても再実行すれば正しい状態になる
- ステータス変更などのデータ更新にも対応できる
- テーブルをロックせずに行単位で更新できる

### 採用による懸念点

- `to_sql()` など pandas 組み込みメソッドが使えず、SQL を直書きする必要がある
- 大量データの一括 Upsert は全件 INSERT よりやや遅い

---

## 各選択肢の比較

### A. INSERT ON CONFLICT DO UPDATE（採用）

**良い点**
- べき等。何度実行しても結果が同じ
- UPDATE と INSERT を 1 クエリで処理できる（アトミック）
- 行単位で操作するためテーブルロックが不要

**懸念点**
- SQL を手書きする必要がある（`to_sql()` が使えない）

---

### B. 全件 DELETE → INSERT（洗い替え）

**良い点**
- 実装がシンプル
- テーブルの内容が常に最新の CSV と一致することが保証される

**懸念点**
- DELETE と INSERT の間、テーブルが空になる（外部キー参照がある場合は特に危険）
- 大量データでは処理時間が長く、ダウンタイムが発生する可能性がある
- 分析クエリが走っているタイミングで DELETE すると、空のデータが返る可能性がある

---

### C. INSERT のみ（重複時はスキップ）

**良い点**
- 既存データを変更しない。意図しない上書きが起きない

**懸念点**
- ステータス変更（`pending` → `completed`）などのデータ更新に対応できない
- 再取込時に「変更されたはずのデータが古いまま」になるリスクがある

---

### D. pandas の `to_sql(if_exists="replace")`

**良い点**
- 実装が 1 行で済む

**懸念点**
- `"replace"` はテーブルを DROP して再作成するため、PRIMARY KEY / インデックスなどの制約が失われる
- べき等でない（制約が毎回消える）
- STEP 1（学習用の全件ロード）のみで採用し、STEP 4 以降では使用しない

---

## 参考

- [PostgreSQL ON CONFLICT ドキュメント](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT)
- 実装: `src/load/writer.py`（`upsert_orders`）、`src/load/dwh_loader.py`（各 dim / fact への Upsert）
