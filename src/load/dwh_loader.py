from sqlalchemy import text


def create_dwh_tables(engine) -> None:
    """dim/fact テーブルが存在しなければ作成する。"""
    ddl = """
    CREATE TABLE IF NOT EXISTS dim_customer (
        customer_id   VARCHAR(10)  PRIMARY KEY,
        customer_name VARCHAR(100) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dim_product (
        product_id   VARCHAR(10)  PRIMARY KEY,
        product_name VARCHAR(100) NOT NULL,
        unit_price   INTEGER      NOT NULL
    );

    -- 日付ディメンション: 1日1行。year/quarter/month/day を持つ
    CREATE TABLE IF NOT EXISTS dim_date (
        date_id  DATE    PRIMARY KEY,
        year     INTEGER NOT NULL,
        quarter  INTEGER NOT NULL,
        month    INTEGER NOT NULL,
        day      INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS fact_orders (
        order_id    VARCHAR(20) PRIMARY KEY,
        customer_id VARCHAR(10) NOT NULL REFERENCES dim_customer(customer_id),
        product_id  VARCHAR(10) NOT NULL REFERENCES dim_product(product_id),
        order_date  DATE        NOT NULL REFERENCES dim_date(date_id),
        quantity    INTEGER     NOT NULL,
        unit_price  INTEGER     NOT NULL,
        amount      INTEGER     NOT NULL,  -- quantity × unit_price
        status      VARCHAR(20) NOT NULL
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    print("[DWH] dim/fact テーブルを準備しました。")


def upsert_dim_customer(engine) -> None:
    """orders ステージングから dim_customer へ Upsert する。"""
    # DISTINCT ON で customer_id ごとに1行に絞る（同じIDに複数の名前がある場合に対応）
    sql = """
    INSERT INTO dim_customer (customer_id, customer_name)
    SELECT DISTINCT ON (customer_id) customer_id, customer_name FROM orders
    ON CONFLICT (customer_id) DO UPDATE
        SET customer_name = EXCLUDED.customer_name
    """
    with engine.begin() as conn:
        result = conn.execute(text(sql))
    print(f"[DWH] dim_customer を更新しました（{result.rowcount} 件）。")


def upsert_dim_product(engine) -> None:
    """orders ステージングから dim_product へ Upsert する。"""
    sql = """
    INSERT INTO dim_product (product_id, product_name, unit_price)
    SELECT DISTINCT product_id, product_name, unit_price FROM orders
    ON CONFLICT (product_id) DO UPDATE
        SET product_name = EXCLUDED.product_name,
            unit_price   = EXCLUDED.unit_price
    """
    with engine.begin() as conn:
        result = conn.execute(text(sql))
    print(f"[DWH] dim_product を更新しました（{result.rowcount} 件）。")


def upsert_dim_date(engine) -> None:
    """orders ステージングの order_date から dim_date へ Upsert する。"""
    sql = """
    INSERT INTO dim_date (date_id, year, quarter, month, day)
    SELECT DISTINCT
        order_date::date                          AS date_id,
        EXTRACT(YEAR    FROM order_date)::INTEGER AS year,
        EXTRACT(QUARTER FROM order_date)::INTEGER AS quarter,
        EXTRACT(MONTH   FROM order_date)::INTEGER AS month,
        EXTRACT(DAY     FROM order_date)::INTEGER AS day
    FROM orders
    ON CONFLICT (date_id) DO NOTHING
    """
    with engine.begin() as conn:
        result = conn.execute(text(sql))
    print(f"[DWH] dim_date を更新しました（{result.rowcount} 件）。")


def upsert_fact_orders(engine) -> None:
    """orders ステージングから fact_orders へ Upsert する。amount を計算して付与する。"""
    sql = """
    INSERT INTO fact_orders
        (order_id, customer_id, product_id, order_date, quantity, unit_price, amount, status)
    SELECT
        order_id,
        customer_id,
        product_id,
        order_date::date,
        quantity,
        unit_price,
        quantity * unit_price AS amount,
        status
    FROM orders
    ON CONFLICT (order_id) DO UPDATE SET
        customer_id = EXCLUDED.customer_id,
        product_id  = EXCLUDED.product_id,
        order_date  = EXCLUDED.order_date,
        quantity    = EXCLUDED.quantity,
        unit_price  = EXCLUDED.unit_price,
        amount      = EXCLUDED.amount,
        status      = EXCLUDED.status
    """
    with engine.begin() as conn:
        result = conn.execute(text(sql))
    print(f"[DWH] fact_orders を更新しました（{result.rowcount} 件）。")
