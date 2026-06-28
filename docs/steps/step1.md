# STEP 1 - 最小 ETL（全件ロード）

## 目的
ETL の最もシンプルな形を動かす。
「CSV を読んで PostgreSQL に全件入れる」だけのパイプラインを最初に動かすことで、
後のステップで何を改善しているかが分かりやすくなる。

## ETL とは

```
Extract（抽出）→ Transform（変換）→ Load（書き込み）
```

- **Extract**: データソース（CSV / API / DB）からデータを取り出す
- **Transform**: クレンジング・検証・集計・正規化を行う
- **Load**: 変換済みデータを DB や DWH に書き込む

STEP 1 では Transform は省略し、Extract → Load の最小構成を実装。

## 作成したファイル

### `data/generate.py` — テストデータ生成

`Faker("ja_JP")` を使って架空の EC サイト注文データを 1000 件生成し、`data/orders.csv` に出力する。

```
order_id, customer_id, customer_name, product_id, product_name,
quantity, unit_price, order_date, status
```

| 項目 | 内容 |
|---|---|
| 商品 | 5種類（ワイヤレスイヤホン, スマートウォッチ, etc.） |
| ステータス | completed / pending / cancelled |
| 注文日 | 2024-01-01 〜 2024-12-31 のランダム |

```bash
# 実行方法
.venv/bin/python data/generate.py
```

---

### `src/extract/reader.py` — CSV 読み込み（Extract）

```python
def read_orders_csv(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, parse_dates=["order_date"])
    return df
```

- `pd.read_csv()` で CSV を pandas DataFrame として読み込む
- `parse_dates=["order_date"]` で日付列を文字列ではなく datetime 型として扱う

> **DataFrame とは？**
> 表（スプレッドシート）をプログラムで扱えるようにしたデータ構造。
> 行・列でデータを操作できる。

---

### `src/load/writer.py` — PostgreSQL 書き込み（Load）

```python
def load_orders(df: pd.DataFrame, engine) -> None:
    df.to_sql(
        name="orders",
        con=engine,
        if_exists="replace",  # テーブルを消して全件入れ直す
        index=False,
    )
```

- **SQLAlchemy**: Python から DB に接続するためのライブラリ
- **`create_engine()`**: DB への接続設定を作る
- **`df.to_sql()`**: DataFrame の内容をそのまま DB テーブルに書き込む
- **`if_exists="replace"`**: 既存テーブルを DROP して全件再投入（STEP 4 で Upsert に改修予定）

---

### `main.py` — パイプラインの司令塔

```python
def run():
    df = read_orders_csv(CSV_PATH)   # Extract
    engine = get_engine()
    create_table(engine)
    load_orders(df, engine)          # Load
```

各モジュールを呼び出して Extract → Load を実行する。

## 実行方法

```bash
# 1. テストデータ生成
.venv/bin/python data/generate.py

# 2. ETL 実行
.venv/bin/python main.py

# 3. DB 確認
docker exec -it batch_postgres psql -U batch_user -d batch_db -c "SELECT COUNT(*) FROM orders;"
```

## 学んだ概念

| 概念 | 説明 |
|---|---|
| pandas DataFrame | 表形式データをプログラムで操作するデータ構造 |
| `parse_dates` | CSV 読み込み時に指定列を datetime 型として扱う |
| SQLAlchemy | Python と DB をつなぐライブラリ（接続・SQL実行・ORM） |
| `df.to_sql()` | DataFrame を DB テーブルに一括書き込みする |
| `if_exists="replace"` | 全件ロード（STEP 4 で Upsert に変わる） |
| Faker | ダミーデータを自動生成するライブラリ |

## 次のステップ（STEP 2）での改善点
- `if_exists="replace"` は本番では使えない（既存データが消える）
- データの型や値が正しいか確認していない（数量がマイナスでも通ってしまう）
- → Pydantic / Pandera でバリデーションを追加する
