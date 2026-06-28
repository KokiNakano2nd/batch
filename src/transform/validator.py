from datetime import date
from typing import Literal

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
from pydantic import BaseModel, field_validator, ValidationError


# ---------------------------------------------------------------------------
# Pydantic: 1行ずつ型・値を検証するモデル
# ---------------------------------------------------------------------------

VALID_STATUSES = {"completed", "pending", "cancelled"}
VALID_PRODUCT_IDS = {"P001", "P002", "P003", "P004", "P005"}


class OrderRow(BaseModel):
    order_id: str
    customer_id: str
    customer_name: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: int
    order_date: date
    status: Literal["completed", "pending", "cancelled"]

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"quantity は 1 以上である必要があります（実際の値: {v}）")
        return v

    @field_validator("unit_price")
    @classmethod
    def unit_price_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"unit_price は 1 以上である必要があります（実際の値: {v}）")
        return v

    @field_validator("product_id")
    @classmethod
    def product_id_must_be_valid(cls, v: str) -> str:
        if v not in VALID_PRODUCT_IDS:
            raise ValueError(f"未知の product_id です: {v}")
        return v


def validate_rows_with_pydantic(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame の各行を Pydantic モデルで検証する。
    エラーがあった行を報告し、正常な行だけを返す。
    """
    valid_rows = []
    error_count = 0

    for _, row in df.iterrows():
        try:
            OrderRow(**row.to_dict())
            valid_rows.append(row)
        except ValidationError as e:
            error_count += 1
            print(f"[Validate][Pydantic] エラー行 order_id={row['order_id']}: {e.errors()[0]['msg']}")

    if error_count > 0:
        print(f"[Validate][Pydantic] {error_count} 件のエラー行を除外しました。")
    else:
        print(f"[Validate][Pydantic] 全 {len(df)} 件が正常です。")

    return pd.DataFrame(valid_rows).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Pandera: DataFrame 全体の構造・型・値域を検証するスキーマ
# ---------------------------------------------------------------------------

ORDER_SCHEMA = DataFrameSchema(
    columns={
        "order_id":      Column(str, nullable=False),
        "customer_id":   Column(str, nullable=False),
        "customer_name": Column(str, nullable=False),
        "product_id":    Column(str, Check.isin(VALID_PRODUCT_IDS), nullable=False),
        "product_name":  Column(str, nullable=False),
        "quantity":      Column(int, Check.greater_than(0), nullable=False),
        "unit_price":    Column(int, Check.greater_than(0), nullable=False),
        "order_date":    Column("datetime64[ns]", nullable=False),
        "status":        Column(str, Check.isin(VALID_STATUSES), nullable=False),
    },
    checks=[
        # DataFrame 全体に対するチェック（列をまたぐ検証など）
        Check(lambda df: df["order_id"].is_unique, error="order_id に重複があります"),
    ],
)


def validate_dataframe_with_pandera(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pandera スキーマで DataFrame 全体の構造を検証する。
    検証エラーがあった場合は例外を送出する。
    """
    try:
        validated_df = ORDER_SCHEMA.validate(df, lazy=True)
        print(f"[Validate][Pandera] スキーマ検証 OK（{len(validated_df)} 件）")
        return validated_df
    except pa.errors.SchemaErrors as e:
        print(f"[Validate][Pandera] スキーマエラーが {len(e.failure_cases)} 件見つかりました:")
        print(e.failure_cases[["column", "check", "failure_case"]].to_string(index=False))
        raise


# ---------------------------------------------------------------------------
# 外部から呼び出すメイン関数
# ---------------------------------------------------------------------------

def validate_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pydantic（行レベル）→ Pandera（DataFrame レベル）の順で検証する。
    """
    print("[Validate] 検証を開始します...")

    # Step 1: 行レベルの検証（エラー行を除外して続行）
    df = validate_rows_with_pydantic(df)

    # Step 2: DataFrame レベルの構造・型検証（エラーがあれば例外）
    df = validate_dataframe_with_pandera(df)

    print(f"[Validate] 検証完了。{len(df)} 件が後続処理に渡ります。")
    return df
