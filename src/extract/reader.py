from datetime import date

import pandas as pd


def read_orders_csv(file_path: str, since: date | None = None) -> pd.DataFrame:
    """
    CSV を読み込んで DataFrame を返す。
    since を指定すると order_date が since より新しい行だけを返す（増分抽出）。
    """
    df = pd.read_csv(file_path, parse_dates=["order_date"])

    if since is not None:
        df = df[df["order_date"].dt.date > since].reset_index(drop=True)
        print(f"[Extract] {len(df)} 件を増分抽出しました（{since} より新しい行）。")
    else:
        print(f"[Extract] {len(df)} 件を全件読み込みました（初回）。")

    return df
