"""
pandas / polars / DuckDB の速度比較ベンチマーク。

計測対象:
  1. CSV 読み込み（10 万件）
  2. 増分抽出（since フィルタ）
  3. 月別売上集計

実行方法:
    .venv/bin/python scripts/benchmark.py
"""

import sys
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

# プロジェクトルートを sys.path に追加（src パッケージを import できるようにする）
sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb
import pandas as pd
import polars as pl

from src.extract.reader import read_orders_csv
from src.extract.reader_polars import read_orders_csv_polars
from src.transform.duckdb_aggregator import monthly_sales_duckdb

CSV_PATH = str(Path(__file__).parent.parent / "data" / "orders_large.csv")
SINCE = date(2023, 1, 1)


@contextmanager
def timer(label: str):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"  {label:<40} {elapsed * 1000:>8.1f} ms")


def bench_read() -> None:
    print("\n── CSV 読み込み（10 万件）─────────────────────")
    with timer("pandas  read_csv"):
        df_pd = pd.read_csv(CSV_PATH, parse_dates=["order_date"])

    with timer("polars  scan_csv + collect"):
        df_pl = pl.scan_csv(CSV_PATH, try_parse_dates=True).collect()

    with timer("duckdb  read_csv_auto"):
        df_dk = duckdb.sql(f"SELECT * FROM read_csv_auto('{CSV_PATH}')").df()

    print(f"  行数: pandas={len(df_pd):,}  polars={len(df_pl):,}  duckdb={len(df_dk):,}")


def bench_filter() -> None:
    print("\n── 増分抽出（2023-01-01 以降）────────────────")
    with timer("pandas  (read + filter)"):
        df_pd = read_orders_csv(CSV_PATH, since=SINCE)

    with timer("polars  (scan + filter + collect)"):
        df_pl = read_orders_csv_polars(CSV_PATH, since=SINCE)

    with timer("duckdb  (SQL WHERE)"):
        df_dk = duckdb.sql(
            f"SELECT * FROM read_csv_auto('{CSV_PATH}') WHERE order_date > '{SINCE}'"
        ).df()

    print(f"  抽出行数: pandas={len(df_pd):,}  polars={len(df_pl):,}  duckdb={len(df_dk):,}")


def bench_aggregate() -> None:
    print("\n── 月別売上集計 ────────────────────────────")
    with timer("pandas  (groupby)"):
        df = pd.read_csv(CSV_PATH, parse_dates=["order_date"])
        df = df[df["status"] == "completed"].copy()
        df["year"]  = df["order_date"].dt.year
        df["month"] = df["order_date"].dt.month
        result_pd = (
            df.groupby(["year", "month"])
            .agg(total_amount=("unit_price", lambda x: (x * df.loc[x.index, "quantity"]).sum()),
                 order_count=("order_id", "count"))
            .reset_index()
        )

    with timer("polars  (groupby)"):
        result_pl = (
            pl.scan_csv(CSV_PATH, try_parse_dates=True)
            .filter(pl.col("status") == "completed")
            .with_columns([
                pl.col("order_date").dt.year().alias("year"),
                pl.col("order_date").dt.month().alias("month"),
                (pl.col("quantity") * pl.col("unit_price")).alias("amount"),
            ])
            .group_by(["year", "month"])
            .agg([
                pl.col("amount").sum().alias("total_amount"),
                pl.col("order_id").count().alias("order_count"),
            ])
            .sort(["year", "month"])
            .collect()
        )

    with timer("duckdb  (SQL GROUP BY)"):
        result_dk = monthly_sales_duckdb(CSV_PATH)

    print(f"  集計行数: pandas={len(result_pd):,}  polars={len(result_pl):,}  duckdb={len(result_dk):,}")


def main() -> None:
    print("=" * 55)
    print("  ベンチマーク開始（データ: orders_large.csv / 10 万件）")
    print("=" * 55)

    bench_read()
    bench_filter()
    bench_aggregate()

    print("\n" + "=" * 55)
    print("  完了")
    print("=" * 55)


if __name__ == "__main__":
    main()
