"""
src/load/writer.py の単体テスト

Load はデータベースに書き込む処理なので、実際に DB に接続するとテストが重くなる。
ここでは「モック（Mock）」を使って DB を偽物に差し替え、
「正しい SQL が実行されたか」「df.to_sql が呼ばれたか」だけを確認する。

モックとは：本物の代わりに使う「偽物オブジェクト」。
  呼ばれたか、何回呼ばれたか、どんな引数で呼ばれたかを記録してくれる。
"""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from src.load.writer import create_table, load_orders


class TestCreateTable:
    def test_executes_ddl(self):
        """create_table は engine.connect() 経由で SQL を実行すること。"""
        # DB エンジンの偽物を作る
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        # "with engine.connect() as conn:" の部分を偽物にする
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        create_table(mock_engine)

        # conn.execute() が1回呼ばれたことを確認
        mock_conn.execute.assert_called_once()

    def test_commits_after_execute(self):
        """create_table はテーブル作成後に commit すること。"""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        create_table(mock_engine)

        mock_conn.commit.assert_called_once()


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

        # df.to_sql をモックに差し替える
        with patch.object(df, "to_sql") as mock_to_sql:
            load_orders(df, mock_engine)
            mock_to_sql.assert_called_once()

    def test_to_sql_uses_correct_table_name(self):
        """load_orders は 'orders' テーブルに書き込むこと。"""
        mock_engine = MagicMock()
        df = self._make_df()

        with patch.object(df, "to_sql") as mock_to_sql:
            load_orders(df, mock_engine)
            # to_sql に渡された name 引数が "orders" であること
            args, kwargs = mock_to_sql.call_args
            assert kwargs.get("name") == "orders" or args[0] == "orders"
