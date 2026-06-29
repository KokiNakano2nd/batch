# STEP 5 - ディメンショナルモデリング

## 目的

フラットな1枚テーブル（`orders`）を「星型スキーマ（Star Schema）」に分割する。
分析に使いやすいテーブル構造を作り、集計クエリを実装する。

---

## やったこと

### 作成・変更したファイル

| ファイル | 内容 |
|---|---|
| `src/load/dwh_loader.py` | 新規作成。dim/fact テーブルの DDL 作成・各テーブルへの Upsert 関数を実装。 |
| `src/transform/aggregator.py` | 新規作成。月別売上・商品別ランキング・ステータス別集計の3つのクエリ関数を実装。 |
| `main.py` | DWH ローディングステップを追加。ステージング → dim → fact の順でデータを流す。 |
| `src/load/writer.py` | `create_table` に PRIMARY KEY 後付け処理を追加（STEP1 の `to_sql` が制約なしで作ったテーブルへの対応）。 |
| `tests/test_dwh_loader.py` | 新規作成。dim/fact ローダーのモックテスト（10件）。 |
| `tests/test_aggregator.py` | 新規作成。集計クエリのモックテスト（6件）。 |

### 実際の DB 結果（1000件ロード後）

```
 tbl          | count
--------------+-------
 dim_customer |   195
 dim_product  |     5
 dim_date     |   339
 fact_orders  |  1000

月別売上サンプル:
 year | month | total_amount | order_count
------+-------+--------------+-------------
 2024 |     1 |      2444240 |          81
 2024 |     2 |      2345420 |          84
```

---

## 学んだ概念

### 星型スキーマ（Star Schema）

中央に「ファクトテーブル（測定値）」を置き、周囲に「ディメンションテーブル（属性）」をつなぐ構造。

```
                ┌─────────────┐
                │ dim_customer│
                └──────┬──────┘
                       │
┌─────────────┐  ┌─────┴──────────┐  ┌─────────────┐
│  dim_product├──┤  fact_orders   ├──┤   dim_date  │
└─────────────┘  └────────────────┘  └─────────────┘
```

- **ファクトテーブル（fact）**: 数値データ（金額・数量など）と FK の集合
- **ディメンションテーブル（dim）**: 属性データ（名前・カテゴリ・日付の内訳など）

### ステージング → DWH のパターン

```
CSV → orders（ステージング）→ dim/fact（DWH）
```

`orders` を一時的な保管場所（ステージング）にして、そこから整形・変換した結果を DWH へ流す設計。
生データと分析用データを分けることで、後から変換ロジックを変えやすくなる。

### dim_date（日付ディメンション）

`order_date` 1カラムから `year / quarter / month / day` を展開して専用テーブルにする。
これにより「月ごと」「四半期ごと」の集計を GROUP BY だけで書けるようになる。

```sql
SELECT d.year, d.month, SUM(f.amount)
FROM fact_orders f
JOIN dim_date d ON f.order_date = d.date_id
GROUP BY d.year, d.month
```

### DISTINCT ON（PostgreSQL 固有）

同じ `customer_id` に異なる名前が複数ある場合、`DISTINCT` だけでは複数行が残り
`ON CONFLICT DO UPDATE` がエラーになる。`DISTINCT ON (customer_id)` で1件に絞る。

```sql
-- NG: DISTINCT だけだと customer_id が重複しうる
SELECT DISTINCT customer_id, customer_name FROM orders

-- OK: customer_id ごとに1行に絞る
SELECT DISTINCT ON (customer_id) customer_id, customer_name FROM orders
```

### amount カラム（派生メジャー）

`fact_orders.amount = quantity × unit_price` をロード時に計算して格納している。
集計クエリで毎回掛け算せずに `SUM(amount)` で済むためパフォーマンスが上がる。

---

## 次のステップでの改善点

- 現状の集計クエリは Python から呼び出すだけ。STEP 6 で Prefect にラップして
  スケジュール実行・リトライができるジョブとして管理できるようになる。
- `dim_customer` は「最後に登場した名前」で上書きしているため、
  顧客名の変更履歴を残したい場合は SCD（Slowly Changing Dimension）という手法が必要になる。
