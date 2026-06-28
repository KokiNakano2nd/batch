from src.extract.reader import read_orders_csv
from src.load.writer import get_engine, create_table, load_orders

CSV_PATH = "data/orders.csv"


def run():
    print("=== ETL 開始 ===")

    # Extract
    df = read_orders_csv(CSV_PATH)

    # Load
    engine = get_engine()
    create_table(engine)
    load_orders(df, engine)

    print("=== ETL 完了 ===")


if __name__ == "__main__":
    run()
