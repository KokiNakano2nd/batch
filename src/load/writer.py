import os

import pandas as pd
from sqlalchemy import create_engine, text

# 環境変数 DATABASE_URL があればそれを使う。なければローカル開発用のデフォルト値。
# Docker Compose では DATABASE_URL=postgresql://...@postgres:5432/batch_db が設定される。
_DEFAULT_DB_URL = "postgresql://batch_user:batch_pass@localhost:5432/batch_db"
DB_URL = os.environ.get("DATABASE_URL", _DEFAULT_DB_URL)


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
    # STEP1 で to_sql が制約なしでテーブルを作った場合に PRIMARY KEY を後付けする
    add_pk = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'orders'::regclass AND contype = 'p'
        ) THEN
            ALTER TABLE orders ADD PRIMARY KEY (order_id);
        END IF;
    END $$;
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
        conn.execute(text(add_pk))
    print("[Load] テーブルを準備しました。")


def load_orders(df: pd.DataFrame, engine) -> None:
    df.to_sql(
        name="orders",
        con=engine,
        if_exists="replace",  # テーブルを一度消して全件入れ直す（STEP1は全件ロード）
        index=False,
    )
    print(f"[Load] {len(df)} 件を PostgreSQL にロードしました。")


def upsert_orders(df: pd.DataFrame, engine) -> None:
    """
    order_id をキーにして Upsert（INSERT ON CONFLICT DO UPDATE）を行う。
    同じ order_id がすでに存在すれば全カラムを上書きする。べき等な操作。
    """
    sql = text("""
    INSERT INTO orders (
        order_id, customer_id, customer_name, product_id, product_name,
        quantity, unit_price, order_date, status
    ) VALUES (
        :order_id, :customer_id, :customer_name, :product_id, :product_name,
        :quantity, :unit_price, :order_date, :status
    )
    ON CONFLICT (order_id) DO UPDATE SET
        customer_id   = EXCLUDED.customer_id,
        customer_name = EXCLUDED.customer_name,
        product_id    = EXCLUDED.product_id,
        product_name  = EXCLUDED.product_name,
        quantity      = EXCLUDED.quantity,
        unit_price    = EXCLUDED.unit_price,
        order_date    = EXCLUDED.order_date,
        status        = EXCLUDED.status
    """)
    records = df.to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(sql, records)
    print(f"[Load] {len(df)} 件を Upsert しました。")
