from src.extract.reader import read_orders_csv
from src.transform.validator import validate_orders
from src.load.writer import get_engine, create_table, upsert_orders
from src.load.watermark import create_watermark_table, get_watermark, update_watermark
from src.load.dwh_loader import (
    create_dwh_tables,
    upsert_dim_customer,
    upsert_dim_product,
    upsert_dim_date,
    upsert_fact_orders,
)

CSV_PATH = "data/orders.csv"
JOB_NAME = "orders_etl"


def run():
    print("=== ETL 開始 ===")

    engine = get_engine()

    # スキーマ準備
    create_table(engine)            # orders（ステージング）
    create_watermark_table(engine)  # watermarks
    create_dwh_tables(engine)       # dim_* / fact_orders（DWH層）

    # Watermark 取得（初回は None → 全件、2回目以降は前回最終日以降のみ）
    last_loaded = get_watermark(engine, JOB_NAME)
    if last_loaded:
        print(f"[Watermark] 前回最終取込日: {last_loaded}（増分モード）")
    else:
        print("[Watermark] 初回実行（全件モード）")

    # Extract（増分）
    df = read_orders_csv(CSV_PATH, since=last_loaded)

    if df.empty:
        print("=== 新規データなし。ETL をスキップします。===")
        return

    # Transform（検証）
    df = validate_orders(df)

    # Load ステージング（orders テーブルへ Upsert）
    upsert_orders(df, engine)

    # Load DWH（dim → fact の順で Upsert）
    print("[DWH] ディメンション・ファクトテーブルを更新します...")
    upsert_dim_customer(engine)
    upsert_dim_product(engine)
    upsert_dim_date(engine)
    upsert_fact_orders(engine)

    # Watermark を今回ロードした最新日付に更新
    new_watermark = df["order_date"].dt.date.max()
    update_watermark(engine, JOB_NAME, new_watermark)

    print("=== ETL 完了 ===")


if __name__ == "__main__":
    run()
