"""
polars 版 CSV リーダー。

pandas 版（reader.py）と同じインターフェースで増分抽出を実装する。
polars の特徴:
  - Lazy evaluation（lazy()）: 実際の読み込みを collect() まで遅延させ、不要なデータを読まない
  - メソッドチェーンで変換を記述する
  - pandas より高速（特に大規模データ）
"""

from datetime import date

import polars as pl


def read_orders_csv_polars(file_path: str, since: date | None = None) -> pl.DataFrame:
    """
    CSV を polars DataFrame として読み込む。

    since を指定すると since より新しい order_date の行だけを返す（増分抽出）。
    lazy() で遅延評価し、フィルタを CSV 読み込み前に適用することでメモリを節約する。
    """
    query = (
        pl.scan_csv(file_path, try_parse_dates=True)  # lazy モードで読み込み
    )

    if since is not None:
        query = query.filter(pl.col("order_date") > since)

    return query.collect()  # ここで初めて実際の読み込みと処理が走る
