"""
DuckDB 版集計クエリ。

DuckDB の特徴:
  - CSV / Parquet ファイルを直接 SQL でクエリできる（DB サーバー不要）
  - ファイルをメモリに全展開せず、必要な列・行だけを読む（列指向ストレージ）
  - pandas の aggregator.py と同じ集計結果を、SQL だけで実現できる
"""

import duckdb
import pandas as pd


def monthly_sales_duckdb(file_path: str) -> pd.DataFrame:
    """月別売上を集計する。pandas の monthly_sales() と同じ結果を返す。"""
    sql = f"""
    SELECT
        YEAR(order_date)  AS year,
        MONTH(order_date) AS month,
        SUM(quantity * unit_price) AS total_amount,
        COUNT(*)                   AS order_count
    FROM read_csv_auto('{file_path}')
    WHERE status = 'completed'
    GROUP BY year, month
    ORDER BY year, month
    """
    return duckdb.sql(sql).df()


def product_sales_ranking_duckdb(file_path: str) -> pd.DataFrame:
    """商品別売上ランキングを集計する。"""
    sql = f"""
    SELECT
        product_name,
        SUM(quantity * unit_price) AS total_amount,
        SUM(quantity)              AS total_quantity
    FROM read_csv_auto('{file_path}')
    WHERE status = 'completed'
    GROUP BY product_name
    ORDER BY total_amount DESC
    """
    return duckdb.sql(sql).df()


def status_summary_duckdb(file_path: str) -> pd.DataFrame:
    """ステータス別集計を行う。"""
    sql = f"""
    SELECT
        status,
        COUNT(*)                   AS order_count,
        SUM(quantity * unit_price) AS total_amount
    FROM read_csv_auto('{file_path}')
    GROUP BY status
    ORDER BY order_count DESC
    """
    return duckdb.sql(sql).df()
