# STEP 9-B - polars / DuckDB による大規模データ処理

## 目的

pandas は小〜中規模データには十分だが、数百万行になるとメモリ不足・処理速度の問題が出てくる。
polars と DuckDB を使って「同じ処理を速く・省メモリで書く方法」を学ぶ。

---

## やったこと

### 作成・変更したファイル

| ファイル | 内容 |
|---|---|
| `scripts/generate_large_data.py` | 新規作成。10 万件の CSV（`data/orders_large.csv`）を生成する。 |
| `src/extract/reader_polars.py` | 新規作成。polars の `scan_csv`（Lazy 評価）で増分抽出を実装。 |
| `src/transform/duckdb_aggregator.py` | 新規作成。DuckDB で CSV を直接 SQL クエリして集計。 |
| `scripts/benchmark.py` | 新規作成。pandas / polars / DuckDB の速度を比較する。 |
| `tests/test_reader_polars.py` | 新規作成。polars リーダーのテスト 4 件。 |
| `tests/test_duckdb_aggregator.py` | 新規作成。DuckDB 集計のテスト 7 件。 |
| `requirements.txt` | `polars==1.42.0` / `duckdb==1.5.4` を追加。 |

### ベンチマーク結果（10 万件 / 8 MB）

```
── CSV 読み込み ──────────────────────────────────
  pandas  read_csv                             147.8 ms
  polars  scan_csv + collect                   108.0 ms
  duckdb  read_csv_auto                        199.3 ms

── 増分抽出（2023-01-01 以降）────────────────────
  pandas  (read + filter)                      126.6 ms
  polars  (scan + filter + collect)             27.5 ms  ← 4.6 倍速い
  duckdb  (SQL WHERE)                          124.1 ms

── 月別売上集計（groupby）──────────────────────
  pandas  (groupby)                            132.1 ms
  polars  (groupby)                             33.5 ms  ← 3.9 倍速い
  duckdb  (SQL GROUP BY)                       130.5 ms
```

---

## 学んだ概念

### polars と pandas の書き方の違い

**pandas**
```python
df = pd.read_csv("orders.csv", parse_dates=["order_date"])
df = df[df["order_date"].dt.date > since]  # 全件読んでからフィルタ
```

**polars（Lazy 評価）**
```python
df = (
    pl.scan_csv("orders.csv", try_parse_dates=True)  # まだ読まない
      .filter(pl.col("order_date") > since)           # フィルタを「予約」する
      .collect()                                        # ここで初めて実行
)
```

polars の `scan_csv` は「どう処理するかの計画」だけを立て、実際の読み込みは `collect()` 時にまとめて行う。
これを **Lazy 評価**（遅延評価）という。フィルタや集計が CSV 読み込みと同時に最適化されるため高速。

### polars のメソッドチェーン

```python
result = (
    pl.scan_csv(file_path, try_parse_dates=True)
    .filter(pl.col("status") == "completed")
    .with_columns([
        pl.col("order_date").dt.year().alias("year"),
        (pl.col("quantity") * pl.col("unit_price")).alias("amount"),
    ])
    .group_by(["year", "month"])
    .agg(pl.col("amount").sum().alias("total_amount"))
    .sort(["year", "month"])
    .collect()
)
```

- `pl.col("カラム名")` で列を指定する（pandas の `df["カラム名"]` に相当）
- `.alias("新名前")` で列名を変更する
- `.with_columns()` で列を追加・変換する

### DuckDB — DB サーバーなしで SQL を使う

```python
import duckdb

result = duckdb.sql("""
    SELECT product_name, SUM(quantity * unit_price) AS total_amount
    FROM read_csv_auto('orders_large.csv')
    WHERE status = 'completed'
    GROUP BY product_name
    ORDER BY total_amount DESC
""").df()  # .df() で pandas DataFrame に変換
```

- `read_csv_auto('ファイルパス')` で CSV をそのまま SQL のテーブルとして扱える
- DB のインストール・起動が不要（Python プロセス内で動く）
- 列指向ストレージで処理するため、GROUP BY / WHERE が速い
- `.df()` で pandas DataFrame、`.pl()` で polars DataFrame に変換できる

### 各ツールの使い分け

| 状況 | 推奨ツール |
|---|---|
| 小〜中規模データ（〜100 万行）、既存コードと統合しやすさ重視 | pandas |
| 大規模データ、速度重視、Python ネイティブな変換処理 | polars |
| ファイルを直接 SQL で集計・探索したい | DuckDB |
| 本番 DB（PostgreSQL など）が既にある | SQLAlchemy + pandas |

---

## 次のステップでの改善点

- 今回は 10 万件（8 MB）だが、1 億行（数 GB）になると pandas はメモリ不足になる。
  polars はチャンク処理不要（内部で自動最適化）、DuckDB はファイルをストリームで処理するため、
  どちらも大規模データに対応できる。
- DuckDB は Parquet 形式（列指向の圧縮ファイル）とも直接動作する。
  CSV を Parquet に変換するとさらに高速化できる。
