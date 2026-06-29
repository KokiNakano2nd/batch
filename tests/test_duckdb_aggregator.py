"""
src/transform/duckdb_aggregator.py の単体テスト
"""

import pandas as pd
import pytest

from src.transform.duckdb_aggregator import (
    monthly_sales_duckdb,
    product_sales_ranking_duckdb,
    status_summary_duckdb,
)

SAMPLE_CSV = """\
order_id,customer_id,customer_name,product_id,product_name,quantity,unit_price,order_date,status
ORD-000001,C-0001,田中,P001,イヤホン,2,8800,2024-01-15,completed
ORD-000002,C-0002,鈴木,P002,ウォッチ,1,24800,2024-01-20,completed
ORD-000003,C-0003,佐藤,P001,イヤホン,1,8800,2024-02-10,completed
ORD-000004,C-0004,伊藤,P003,バッテリー,3,3980,2024-02-15,pending
ORD-000005,C-0005,渡辺,P001,イヤホン,1,8800,2024-03-01,cancelled
"""


@pytest.fixture
def sample_csv(tmp_path):
    f = tmp_path / "orders.csv"
    f.write_text(SAMPLE_CSV, encoding="utf-8")
    return str(f)


class TestMonthlySalesDuckdb:
    def test_returns_dataframe(self, sample_csv):
        """戻り値が pandas DataFrame であること。"""
        result = monthly_sales_duckdb(sample_csv)
        assert isinstance(result, pd.DataFrame)

    def test_columns_exist(self, sample_csv):
        """year / month / total_amount / order_count カラムがあること。"""
        result = monthly_sales_duckdb(sample_csv)
        for col in ("year", "month", "total_amount", "order_count"):
            assert col in result.columns

    def test_only_completed_orders(self, sample_csv):
        """status=completed の行だけが集計されること。"""
        result = monthly_sales_duckdb(sample_csv)
        # completed は 3 件（2024-01 が 2 件、2024-02 が 1 件）
        assert result["order_count"].sum() == 3


class TestProductSalesRankingDuckdb:
    def test_returns_dataframe(self, sample_csv):
        result = product_sales_ranking_duckdb(sample_csv)
        assert isinstance(result, pd.DataFrame)

    def test_sorted_by_total_amount_desc(self, sample_csv):
        """total_amount の降順で並んでいること。"""
        result = product_sales_ranking_duckdb(sample_csv)
        amounts = result["total_amount"].tolist()
        assert amounts == sorted(amounts, reverse=True)


class TestStatusSummaryDuckdb:
    def test_returns_dataframe(self, sample_csv):
        result = status_summary_duckdb(sample_csv)
        assert isinstance(result, pd.DataFrame)

    def test_all_statuses_present(self, sample_csv):
        """CSV にある全ステータスが集計されること。"""
        result = status_summary_duckdb(sample_csv)
        statuses = set(result["status"].tolist())
        assert statuses == {"completed", "pending", "cancelled"}
