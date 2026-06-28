"""
src/transform/validator.py の単体テスト

Pydantic（行レベル）と Pandera（DataFrame レベル）それぞれを検証する。
"""

import pandas as pd
import pytest
from src.transform.validator import validate_rows_with_pydantic, validate_dataframe_with_pandera


def make_valid_df(**overrides) -> pd.DataFrame:
    """
    正常な注文 DataFrame を 1 行だけ作るヘルパー関数。
    overrides に渡したフィールドだけ上書きできるので、
    「quantity だけ壊す」などのテストが書きやすくなる。
    """
    base = {
        "order_id":      "ORD-00001",
        "customer_id":   "C-0001",
        "customer_name": "田中太郎",
        "product_id":    "P001",
        "product_name":  "ワイヤレスイヤホン",
        "quantity":      2,
        "unit_price":    8800,
        "order_date":    pd.Timestamp("2024-03-15"),
        "status":        "completed",
    }
    base.update(overrides)
    return pd.DataFrame([base])


# ---------------------------------------------------------------------------
# Pydantic（行レベル）テスト
# ---------------------------------------------------------------------------

class TestPydanticValidation:
    def test_valid_row_passes(self):
        """正常なデータは除外されずにそのまま返ること。"""
        df = make_valid_df()
        result = validate_rows_with_pydantic(df)
        assert len(result) == 1

    def test_quantity_zero_is_rejected(self):
        """quantity=0 の行は除外されること。"""
        df = make_valid_df(quantity=0)
        result = validate_rows_with_pydantic(df)
        assert len(result) == 0

    def test_quantity_negative_is_rejected(self):
        """quantity がマイナスの行は除外されること。"""
        df = make_valid_df(quantity=-1)
        result = validate_rows_with_pydantic(df)
        assert len(result) == 0

    def test_invalid_status_is_rejected(self):
        """定義外の status を持つ行は除外されること。"""
        df = make_valid_df(status="unknown")
        result = validate_rows_with_pydantic(df)
        assert len(result) == 0

    def test_invalid_product_id_is_rejected(self):
        """定義外の product_id を持つ行は除外されること。"""
        df = make_valid_df(product_id="P999")
        result = validate_rows_with_pydantic(df)
        assert len(result) == 0

    def test_mixed_rows_only_valid_passes(self):
        """正常行とエラー行が混在する場合、正常行だけが返ること。"""
        good = make_valid_df(order_id="ORD-00001")
        bad  = make_valid_df(order_id="ORD-00002", quantity=0)
        df = pd.concat([good, bad], ignore_index=True)
        result = validate_rows_with_pydantic(df)
        assert len(result) == 1
        assert result.iloc[0]["order_id"] == "ORD-00001"


# ---------------------------------------------------------------------------
# Pandera（DataFrame レベル）テスト
# ---------------------------------------------------------------------------

class TestPanderaValidation:
    def test_valid_dataframe_passes(self):
        """正常な DataFrame はそのまま返ること。"""
        df = make_valid_df()
        result = validate_dataframe_with_pandera(df)
        assert len(result) == 1

    def test_duplicate_order_id_raises(self):
        """order_id が重複している場合は例外が送出されること。"""
        import pandera.pandas as pa
        row = make_valid_df(order_id="ORD-00001")
        df = pd.concat([row, row], ignore_index=True)  # 同じ order_id を2行
        with pytest.raises(pa.errors.SchemaErrors):
            validate_dataframe_with_pandera(df)

    def test_null_order_id_raises(self):
        """order_id が None の場合は例外が送出されること。"""
        import pandera.pandas as pa
        df = make_valid_df(order_id=None)
        with pytest.raises(pa.errors.SchemaErrors):
            validate_dataframe_with_pandera(df)
