"""
src/transform/aggregator.py の単体テスト

集計クエリは実際に DB へ SELECT を投げる処理なので、
pd.read_sql をモックに差し替えて「返ってきた DataFrame の構造」を確認する。
"""

from unittest.mock import MagicMock, patch
import pandas as pd
from src.transform.aggregator import monthly_sales, product_sales_ranking, status_summary


def _make_mock_engine():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    return mock_engine, mock_conn


class TestMonthlySales:
    def test_returns_dataframe(self):
        """monthly_sales は DataFrame を返すこと。"""
        mock_engine, _ = _make_mock_engine()
        expected = pd.DataFrame([
            {"year": 2024, "month": 1, "total_amount": 100000, "order_count": 10},
        ])
        with patch("src.transform.aggregator.pd.read_sql", return_value=expected):
            result = monthly_sales(mock_engine)
        assert isinstance(result, pd.DataFrame)

    def test_has_expected_columns(self):
        """monthly_sales の結果に year/month/total_amount/order_count 列があること。"""
        mock_engine, _ = _make_mock_engine()
        expected = pd.DataFrame([
            {"year": 2024, "month": 1, "total_amount": 100000, "order_count": 10},
        ])
        with patch("src.transform.aggregator.pd.read_sql", return_value=expected):
            result = monthly_sales(mock_engine)
        assert set(result.columns) == {"year", "month", "total_amount", "order_count"}


class TestProductSalesRanking:
    def test_returns_dataframe(self):
        """product_sales_ranking は DataFrame を返すこと。"""
        mock_engine, _ = _make_mock_engine()
        expected = pd.DataFrame([
            {"product_name": "スマートウォッチ", "total_amount": 500000, "total_quantity": 20},
        ])
        with patch("src.transform.aggregator.pd.read_sql", return_value=expected):
            result = product_sales_ranking(mock_engine)
        assert isinstance(result, pd.DataFrame)

    def test_has_expected_columns(self):
        """product_sales_ranking の結果に product_name/total_amount/total_quantity 列があること。"""
        mock_engine, _ = _make_mock_engine()
        expected = pd.DataFrame([
            {"product_name": "スマートウォッチ", "total_amount": 500000, "total_quantity": 20},
        ])
        with patch("src.transform.aggregator.pd.read_sql", return_value=expected):
            result = product_sales_ranking(mock_engine)
        assert set(result.columns) == {"product_name", "total_amount", "total_quantity"}


class TestStatusSummary:
    def test_returns_dataframe(self):
        """status_summary は DataFrame を返すこと。"""
        mock_engine, _ = _make_mock_engine()
        expected = pd.DataFrame([
            {"status": "completed", "order_count": 700, "total_amount": 3000000},
        ])
        with patch("src.transform.aggregator.pd.read_sql", return_value=expected):
            result = status_summary(mock_engine)
        assert isinstance(result, pd.DataFrame)

    def test_has_expected_columns(self):
        """status_summary の結果に status/order_count/total_amount 列があること。"""
        mock_engine, _ = _make_mock_engine()
        expected = pd.DataFrame([
            {"status": "completed", "order_count": 700, "total_amount": 3000000},
        ])
        with patch("src.transform.aggregator.pd.read_sql", return_value=expected):
            result = status_summary(mock_engine)
        assert set(result.columns) == {"status", "order_count", "total_amount"}
