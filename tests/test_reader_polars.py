"""
src/extract/reader_polars.py の単体テスト
"""

from datetime import date
from pathlib import Path
import tempfile

import polars as pl
import pytest

from src.extract.reader_polars import read_orders_csv_polars

SAMPLE_CSV = """\
order_id,customer_id,customer_name,product_id,product_name,quantity,unit_price,order_date,status
ORD-000001,C-0001,田中太郎,P001,ワイヤレスイヤホン,1,8800,2024-01-15,completed
ORD-000002,C-0002,鈴木花子,P002,スマートウォッチ,2,24800,2024-03-20,completed
ORD-000003,C-0003,佐藤一郎,P003,モバイルバッテリー,1,3980,2023-11-10,pending
"""


@pytest.fixture
def sample_csv(tmp_path):
    f = tmp_path / "orders.csv"
    f.write_text(SAMPLE_CSV, encoding="utf-8")
    return str(f)


class TestReadOrdersCsvPolars:
    def test_returns_polars_dataframe(self, sample_csv):
        """戻り値が polars DataFrame であること。"""
        df = read_orders_csv_polars(sample_csv)
        assert isinstance(df, pl.DataFrame)

    def test_reads_all_rows_without_since(self, sample_csv):
        """since 未指定のとき全件を返すこと。"""
        df = read_orders_csv_polars(sample_csv)
        assert len(df) == 3

    def test_filters_by_since(self, sample_csv):
        """since を指定すると since より新しい行だけを返すこと。"""
        df = read_orders_csv_polars(sample_csv, since=date(2024, 1, 1))
        assert len(df) == 2
        dates = df["order_date"].to_list()
        assert all(d > date(2024, 1, 1) for d in dates)

    def test_returns_empty_when_no_new_rows(self, sample_csv):
        """since が最新日より大きいとき空の DataFrame を返すこと。"""
        df = read_orders_csv_polars(sample_csv, since=date(2025, 1, 1))
        assert len(df) == 0
