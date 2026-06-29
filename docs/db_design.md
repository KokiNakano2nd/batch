# DB 設計書

## 1. 概要

本システムは ECサイトの注文データを処理する ETL パイプラインである。  
DB は **PostgreSQL 16**（Docker コンテナ `batch_postgres`）を使用する。

テーブルは役割によって 3 層に分かれる。

| 層 | テーブル | 役割 |
|---|---|---|
| ステージング層 | `orders` | CSV から取り込んだ生データを保持する |
| DWH 層（ディメンション） | `dim_customer` / `dim_product` / `dim_date` | マスターデータを正規化して保持する |
| DWH 層（ファクト） | `fact_orders` | 集計・分析に使う取引データを保持する |
| 管理層 | `watermarks` | ETL の増分取込状態を管理する |

---

## 2. ER 図

```mermaid
erDiagram
    orders {
        varchar order_id PK
        varchar customer_id
        varchar customer_name
        varchar product_id
        varchar product_name
        integer quantity
        integer unit_price
        date    order_date
        varchar status
    }

    dim_customer {
        varchar customer_id PK
        varchar customer_name
    }

    dim_product {
        varchar product_id PK
        varchar product_name
        integer unit_price
    }

    dim_date {
        date    date_id PK
        integer year
        integer quarter
        integer month
        integer day
    }

    fact_orders {
        varchar order_id    PK
        varchar customer_id FK
        varchar product_id  FK
        date    order_date  FK
        integer quantity
        integer unit_price
        integer amount
        varchar status
    }

    watermarks {
        varchar job_name       PK
        date    last_loaded_at
    }

    fact_orders }o--|| dim_customer : "customer_id"
    fact_orders }o--|| dim_product  : "product_id"
    fact_orders }o--|| dim_date     : "order_date → date_id"
```

---

## 3. テーブル定義

### 3-1. orders（ステージングテーブル）

CSV から取り込んだ注文データをそのまま保持するテーブル。  
DWH への変換前の「一時置き場」として機能する。

| カラム名 | 型 | PK | NOT NULL | 説明 |
|---|---|:---:|:---:|---|
| order_id | VARCHAR(20) | ✓ | ✓ | 注文ID。`ORD-XXXXXX` 形式 |
| customer_id | VARCHAR(10) | | ✓ | 顧客ID。`C-XXXX` 形式 |
| customer_name | VARCHAR(100) | | ✓ | 顧客氏名 |
| product_id | VARCHAR(10) | | ✓ | 商品ID。`P001`〜`P005` のいずれか |
| product_name | VARCHAR(100) | | ✓ | 商品名 |
| quantity | INTEGER | | ✓ | 数量。1 以上 |
| unit_price | INTEGER | | ✓ | 単価（円）。1 以上 |
| order_date | DATE | | ✓ | 注文日 |
| status | VARCHAR(20) | | ✓ | 注文ステータス。後述の値域を参照 |

**status の値域**

| 値 | 意味 |
|---|---|
| `completed` | 完了 |
| `pending` | 処理中 |
| `cancelled` | キャンセル |

**制約**
- `order_id` は一意（PRIMARY KEY）
- `quantity` は 1 以上（Pydantic バリデーション）
- `unit_price` は 1 以上（Pydantic バリデーション）
- `product_id` は `P001`〜`P005` のいずれか（Pydantic / Pandera バリデーション）

**Upsert キー**: `order_id`  
同一の `order_id` が再取込された場合は全カラムを上書きする（`INSERT ON CONFLICT DO UPDATE`）。

---

### 3-2. dim_customer（顧客ディメンション）

顧客マスター。`orders` から `DISTINCT ON (customer_id)` で抽出・Upsert する。

| カラム名 | 型 | PK | NOT NULL | 説明 |
|---|---|:---:|:---:|---|
| customer_id | VARCHAR(10) | ✓ | ✓ | 顧客ID。`C-XXXX` 形式 |
| customer_name | VARCHAR(100) | | ✓ | 顧客氏名 |

**Upsert キー**: `customer_id`  
同一 `customer_id` が再登録された場合は `customer_name` を上書きする。

---

### 3-3. dim_product（商品ディメンション）

商品マスター。`orders` から `DISTINCT product_id` で抽出・Upsert する。

| カラム名 | 型 | PK | NOT NULL | 説明 |
|---|---|:---:|:---:|---|
| product_id | VARCHAR(10) | ✓ | ✓ | 商品ID。`P001`〜`P005` |
| product_name | VARCHAR(100) | | ✓ | 商品名 |
| unit_price | INTEGER | | ✓ | 単価（円） |

**Upsert キー**: `product_id`  
商品名・単価が変更された場合は上書きする。

---

### 3-4. dim_date（日付ディメンション）

日付マスター。`orders` の `order_date` を分解して生成する。  
年・四半期・月・日を持つことで、SQL の集計クエリを簡潔に書けるようになる。

| カラム名 | 型 | PK | NOT NULL | 説明 |
|---|---|:---:|:---:|---|
| date_id | DATE | ✓ | ✓ | 日付（`YYYY-MM-DD`） |
| year | INTEGER | | ✓ | 年 |
| quarter | INTEGER | | ✓ | 四半期（1〜4） |
| month | INTEGER | | ✓ | 月（1〜12） |
| day | INTEGER | | ✓ | 日（1〜31） |

**Upsert キー**: `date_id`  
同一日付が再登録された場合は何もしない（`ON CONFLICT DO NOTHING`）。  
日付の属性は変わらないため上書き不要。

---

### 3-5. fact_orders（注文ファクトテーブル）

分析・集計に使う中心テーブル。各ディメンションテーブルへの外部キーを持つ。  
`amount`（売上金額）は `quantity × unit_price` で計算して格納する（非正規化）。

| カラム名 | 型 | PK | FK | NOT NULL | 説明 |
|---|---|:---:|:---:|:---:|---|
| order_id | VARCHAR(20) | ✓ | | ✓ | 注文ID |
| customer_id | VARCHAR(10) | | dim_customer | ✓ | 顧客ID |
| product_id | VARCHAR(10) | | dim_product | ✓ | 商品ID |
| order_date | DATE | | dim_date | ✓ | 注文日 |
| quantity | INTEGER | | | ✓ | 数量 |
| unit_price | INTEGER | | | ✓ | 単価（円） |
| amount | INTEGER | | | ✓ | 売上金額（quantity × unit_price） |
| status | VARCHAR(20) | | | ✓ | 注文ステータス |

**Upsert キー**: `order_id`  
`orders` からの再ロード時に全カラムを上書きする。

> **なぜ amount を持つか**  
> `quantity × unit_price` の計算を毎回 SELECT 時に行うと集計クエリが遅くなる。  
> あらかじめ計算済みの値を格納しておくことで集計を高速化できる（非正規化の意図的な採用）。

---

### 3-6. watermarks（ウォーターマーク管理テーブル）

増分抽出のための「どこまで取り込んだか」を記録する管理テーブル。  
1 ジョブにつき 1 行を保持する。

| カラム名 | 型 | PK | NOT NULL | 説明 |
|---|---|:---:|:---:|---|
| job_name | VARCHAR(100) | ✓ | ✓ | ジョブ識別名。例: `orders_etl` |
| last_loaded_at | DATE | | ✓ | 最後に取り込んだ注文日 |

**Upsert キー**: `job_name`  
ETL 実行のたびに `last_loaded_at` を最新日に更新する（`INSERT ON CONFLICT DO UPDATE`）。

---

## 4. データフロー

```
CSV ファイル
    │
    ▼
┌─────────────────────────────┐
│  orders（ステージング）       │  ← 全件 Upsert（STEP 1: 全件 / STEP 4: 増分）
└─────────────────────────────┘
    │
    ├──────────────────────────▶  dim_customer（customer_id で Upsert）
    ├──────────────────────────▶  dim_product（product_id で Upsert）
    ├──────────────────────────▶  dim_date（order_date で Upsert）
    │
    └──────────────────────────▶  fact_orders（order_id で Upsert）
                                      ├── FK → dim_customer
                                      ├── FK → dim_product
                                      └── FK → dim_date

watermarks  ←  ETL 完了後に last_loaded_at を更新
```

---

## 5. ロード順序

DWH テーブルへのロードは外部キー制約があるため、以下の順番で行う必要がある。

```
1. dim_customer   （fact_orders が参照するため先にロード）
2. dim_product    （fact_orders が参照するため先にロード）
3. dim_date       （fact_orders が参照するため先にロード）
4. fact_orders    （全ディメンションが揃ってからロード）
5. watermarks     （ETL の最後にウォーターマークを更新）
```

---

## 6. 接続情報

| 項目 | 値 |
|---|---|
| ホスト（ローカル） | `localhost:5432` |
| ホスト（Docker 内） | `postgres:5432`（`batch_postgres` コンテナ名） |
| データベース名 | `batch_db` |
| ユーザー名 | `batch_user` |
| パスワード | `batch_pass` |
| 接続文字列 | `postgresql://batch_user:batch_pass@localhost:5432/batch_db` |

環境変数 `DATABASE_URL` を設定すると接続先を切り替えられる（Docker Compose 環境で使用）。
