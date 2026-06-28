import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql://batch_user:batch_pass@localhost:5432/batch_db"


def get_engine():
    return create_engine(DB_URL)


def create_table(engine) -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS orders (
        order_id      VARCHAR(20) PRIMARY KEY,
        customer_id   VARCHAR(10),
        customer_name VARCHAR(100),
        product_id    VARCHAR(10),
        product_name  VARCHAR(100),
        quantity      INTEGER,
        unit_price    INTEGER,
        order_date    DATE,
        status        VARCHAR(20)
    );
    """
    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()
    print("[Load] テーブルを準備しました。")


def load_orders(df: pd.DataFrame, engine) -> None:
    df.to_sql(
        name="orders",
        con=engine,
        if_exists="replace",  # テーブルを一度消して全件入れ直す（STEP1は全件ロード）
        index=False,
    )
    print(f"[Load] {len(df)} 件を PostgreSQL にロードしました。")
