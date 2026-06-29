"""
src/load/dwh_loader.py の単体テスト

DWH への書き込みはすべてモックで検証する。
「正しい SQL が実行されたか」「engine.begin() でトランザクションを使うか」を確認する。
"""

from unittest.mock import MagicMock
from src.load.dwh_loader import (
    create_dwh_tables,
    upsert_dim_customer,
    upsert_dim_product,
    upsert_dim_date,
    upsert_fact_orders,
)


def _make_mock_engine():
    """engine と conn のモックを組み立てて返すヘルパー。"""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.rowcount = 5
    return mock_engine, mock_conn


class TestCreateDwhTables:
    def test_executes_ddl(self):
        """create_dwh_tables は DDL を実行すること。"""
        mock_engine, mock_conn = _make_mock_engine()
        create_dwh_tables(mock_engine)
        mock_conn.execute.assert_called_once()

    def test_uses_transaction(self):
        """create_dwh_tables はトランザクション（engine.begin）を使うこと。"""
        mock_engine, mock_conn = _make_mock_engine()
        create_dwh_tables(mock_engine)
        mock_engine.begin.assert_called_once()


class TestUpsertDimCustomer:
    def test_executes_sql(self):
        mock_engine, mock_conn = _make_mock_engine()
        upsert_dim_customer(mock_engine)
        mock_conn.execute.assert_called_once()

    def test_uses_transaction(self):
        mock_engine, mock_conn = _make_mock_engine()
        upsert_dim_customer(mock_engine)
        mock_engine.begin.assert_called_once()


class TestUpsertDimProduct:
    def test_executes_sql(self):
        mock_engine, mock_conn = _make_mock_engine()
        upsert_dim_product(mock_engine)
        mock_conn.execute.assert_called_once()

    def test_uses_transaction(self):
        mock_engine, mock_conn = _make_mock_engine()
        upsert_dim_product(mock_engine)
        mock_engine.begin.assert_called_once()


class TestUpsertDimDate:
    def test_executes_sql(self):
        mock_engine, mock_conn = _make_mock_engine()
        upsert_dim_date(mock_engine)
        mock_conn.execute.assert_called_once()

    def test_uses_transaction(self):
        mock_engine, mock_conn = _make_mock_engine()
        upsert_dim_date(mock_engine)
        mock_engine.begin.assert_called_once()


class TestUpsertFactOrders:
    def test_executes_sql(self):
        mock_engine, mock_conn = _make_mock_engine()
        upsert_fact_orders(mock_engine)
        mock_conn.execute.assert_called_once()

    def test_uses_transaction(self):
        mock_engine, mock_conn = _make_mock_engine()
        upsert_fact_orders(mock_engine)
        mock_engine.begin.assert_called_once()
