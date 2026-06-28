import pandas as pd


def read_orders_csv(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, parse_dates=["order_date"])
    print(f"[Extract] {len(df)} 件読み込みました。")
    return df
