"""
src/load/writer.py の単体テスト

Load はデータベースに書き込む処理なので、実際に DB に接続するとテストが重くなる。
ここでは「モック（Mock）」を使って DB を偽物に差し替え、
「正しい SQL が実行されたか」「df.to_sql が呼ばれたか」だけを確認する。

モックとは：本物の代わりに使う「偽物オブジェクト」。
  呼ばれたか、何回呼ばれたか、どんな引数で呼ばれたかを記録してくれる。
"""

from unittest.mock import MagicMock, patch, call
import pandas as pd
import pytest
from src.load.writer import create_table, load_orders, upsert_orders


def _make_mock_engine():
    """engine と conn のモックを返すヘルパー。begin() と connect() 両方に対応。"""
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    return mock_engine, mock_conn


class TestCreateTable:
    def test_executes_ddl(self):
        """create_table は engine.begin() 経由で SQL を実行すること。"""
        mock_engine, mock_conn = _make_mock_engine()
        create_table(mock_engine)
        assert mock_conn.execute.call_count >= 1

    def test_uses_transaction(self):
        """create_table はトランザクション（engine.begin）を使うこと。"""
        mock_engine, mock_conn = _make_mock_engine()
        create_table(mock_engine)
        mock_engine.begin.assert_called_once()


class TestLoadOrders:
    def _make_df(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "order_id":      "ORD-00001",
            "customer_id":   "C-0001",
            "customer_name": "田中太郎",
            "product_id":    "P001",
            "product_name":  "ワイヤレスイヤホン",
            "quantity":      2,
            "unit_price":    8800,
            "order_date":    "2024-03-15",
            "status":        "completed",
        }])

    def test_to_sql_is_called(self):
        """load_orders は df.to_sql() を呼び出すこと。"""
        mock_engine = MagicMock()
        df = self._make_df()

        with patch.object(df, "to_sql") as mock_to_sql:
            load_orders(df, mock_engine)
            mock_to_sql.assert_called_once()

    def test_to_sql_uses_correct_table_name(self):
        """load_orders は 'orders' テーブルに書き込むこと。"""
        mock_engine = MagicMock()
        df = self._make_df()

        with patch.object(df, "to_sql") as mock_to_sql:
            load_orders(df, mock_engine)
            args, kwargs = mock_to_sql.call_args
            assert kwargs.get("name") == "orders" or args[0] == "orders"


class TestUpsertOrders:
    def _make_df(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "order_id":      "ORD-00001",
            "customer_id":   "C-0001",
            "customer_name": "田中太郎",
            "product_id":    "P001",
            "product_name":  "ワイヤレスイヤホン",
            "quantity":      2,
            "unit_price":    8800,
            "order_date":    "2024-03-15",
            "status":        "completed",
        }])

    def test_executes_insert_on_conflict(self):
        """upsert_orders は conn.execute() を呼び出すこと。"""
        mock_engine, mock_conn = _make_mock_engine()
        upsert_orders(self._make_df(), mock_engine)
        mock_conn.execute.assert_called_once()

    def test_uses_transaction(self):
        """upsert_orders はトランザクション（engine.begin）を使うこと。"""
        mock_engine, mock_conn = _make_mock_engine()
        upsert_orders(self._make_df(), mock_engine)
        mock_engine.begin.assert_called_once()

    def test_passes_records_as_list_of_dicts(self):
        """upsert_orders は records を辞書のリストとして conn.execute() に渡すこと。"""
        mock_engine, mock_conn = _make_mock_engine()
        df = self._make_df()
        upsert_orders(df, mock_engine)

        execute_args = mock_conn.execute.call_args[0]
        records_arg = execute_args[1]
        assert isinstance(records_arg, list)
        assert isinstance(records_arg[0], dict)
        assert records_arg[0]["order_id"] == "ORD-00001"
