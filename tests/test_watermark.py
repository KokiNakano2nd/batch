"""
src/load/watermark.py の単体テスト

watermark テーブルへの読み書きをモックで検証する。
"""

from datetime import date
from unittest.mock import MagicMock

from src.load.watermark import create_watermark_table, get_watermark, update_watermark


def _make_mock_engine(fetchone_result=None):
    """engine と conn のモックを組み立てて返すヘルパー。begin() と connect() 両方に対応。"""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchone.return_value = fetchone_result
    return mock_engine, mock_conn


class TestCreateWatermarkTable:
    def test_executes_ddl(self):
        """create_watermark_table は DDL を実行すること。"""
        mock_engine, mock_conn = _make_mock_engine()
        create_watermark_table(mock_engine)
        mock_conn.execute.assert_called_once()

    def test_uses_transaction(self):
        """create_watermark_table はトランザクション（engine.begin）を使うこと。"""
        mock_engine, mock_conn = _make_mock_engine()
        create_watermark_table(mock_engine)
        mock_engine.begin.assert_called_once()


class TestGetWatermark:
    def test_returns_none_when_not_registered(self):
        """未登録の job_name に対して None を返すこと。"""
        mock_engine, _ = _make_mock_engine(fetchone_result=None)
        result = get_watermark(mock_engine, "orders_etl")
        assert result is None

    def test_returns_date_when_registered(self):
        """登録済みの job_name に対して DATE 値を返すこと。"""
        expected = date(2024, 6, 1)
        mock_engine, _ = _make_mock_engine(fetchone_result=(expected,))
        result = get_watermark(mock_engine, "orders_etl")
        assert result == expected


class TestUpdateWatermark:
    def test_executes_upsert_sql(self):
        """update_watermark は INSERT ... ON CONFLICT の SQL を実行すること。"""
        mock_engine, mock_conn = _make_mock_engine()
        update_watermark(mock_engine, "orders_etl", date(2024, 6, 30))
        mock_conn.execute.assert_called_once()

    def test_uses_transaction(self):
        """update_watermark はトランザクション（engine.begin）を使うこと。"""
        mock_engine, mock_conn = _make_mock_engine()
        update_watermark(mock_engine, "orders_etl", date(2024, 6, 30))
        mock_engine.begin.assert_called_once()
