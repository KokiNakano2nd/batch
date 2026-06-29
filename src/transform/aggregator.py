import pandas as pd
from sqlalchemy import text


def monthly_sales(engine) -> pd.DataFrame:
    """
    年月ごとの売上合計と注文件数を返す。
    結果列: year, month, total_amount, order_count
    """
    sql = """
    SELECT
        d.year,
        d.month,
        SUM(f.amount)  AS total_amount,
        COUNT(*)       AS order_count
    FROM fact_orders f
    JOIN dim_date d ON f.order_date = d.date_id
    GROUP BY d.year, d.month
    ORDER BY d.year, d.month
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def product_sales_ranking(engine) -> pd.DataFrame:
    """
    商品別の売上合計と販売数量を降順で返す。
    結果列: product_name, total_amount, total_quantity
    """
    sql = """
    SELECT
        p.product_name,
        SUM(f.amount)   AS total_amount,
        SUM(f.quantity) AS total_quantity
    FROM fact_orders f
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.product_name
    ORDER BY total_amount DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def status_summary(engine) -> pd.DataFrame:
    """
    ステータス別の注文件数と売上合計を返す。
    結果列: status, order_count, total_amount
    """
    sql = """
    SELECT
        status,
        COUNT(*)      AS order_count,
        SUM(amount)   AS total_amount
    FROM fact_orders
    GROUP BY status
    ORDER BY order_count DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df
