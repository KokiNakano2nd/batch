"""
src/extract/reader.py の単体テスト

tmp_path: pytest が自動で用意してくれる「テスト用一時ディレクトリ」。
テスト終了後に自動で削除される。実際の data/orders.csv に依存しないので
テストが独立して動く。
"""

import pandas as pd
import pytest
from src.extract.reader import read_orders_csv


# テスト用の CSV 文字列（最小限の2行）
SAMPLE_CSV = """\
order_id,customer_id,customer_name,product_id,product_name,quantity,unit_price,order_date,status
ORD-00001,C-0001,田中太郎,P001,ワイヤレスイヤホン,2,8800,2024-03-15,completed
ORD-00002,C-0002,鈴木花子,P002,スマートウォッチ,1,24800,2024-05-10,pending
"""


@pytest.fixture
def sample_csv(tmp_path):
    """テスト用 CSV ファイルを一時ディレクトリに作って返す fixture。"""
    csv_file = tmp_path / "orders.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")
    return str(csv_file)


def test_returns_dataframe(sample_csv):
    """CSV を読み込んだ結果が DataFrame であること。"""
    df = read_orders_csv(sample_csv)
    assert isinstance(df, pd.DataFrame)


def test_row_count(sample_csv):
    """サンプル CSV の行数（2行）が正しく読み込まれること。"""
    df = read_orders_csv(sample_csv)
    assert len(df) == 2


def test_columns(sample_csv):
    """期待するすべての列が存在すること。"""
    expected_columns = {
        "order_id", "customer_id", "customer_name",
        "product_id", "product_name", "quantity",
        "unit_price", "order_date", "status",
    }
    df = read_orders_csv(sample_csv)
    assert expected_columns == set(df.columns)


def test_order_date_is_datetime(sample_csv):
    """order_date 列が文字列ではなく datetime 型として読み込まれること。"""
    df = read_orders_csv(sample_csv)
    assert pd.api.types.is_datetime64_any_dtype(df["order_date"])
