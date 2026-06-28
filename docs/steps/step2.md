# STEP 2 - データ検証（Pydantic / Pandera）

## 目的
STEP 1 の ETL は「データが正しい前提」で動いていた。
実際の現場では、想定外のデータ（数量がマイナス、存在しないステータスなど）が混入することがある。
このステップでは「悪いデータを早期に検出・除外する仕組み」を追加する。

## 2つの検証ツール

| ツール | 検証の単位 | 役割 |
|---|---|---|
| **Pydantic** | 1行ずつ | 型・値の制約チェック。エラー行を除外して処理を継続 |
| **Pandera** | DataFrame 全体 | スキーマ・型・一意性などの構造チェック。エラーがあれば処理を止める |

### なぜ2つ使うのか？
- **Pydantic**: 「一部の行が壊れていても、正常な行だけで処理を続けたい」ケースに向く
- **Pandera**: 「DataFrame 全体の構造が壊れているなら処理を止めたい」ケースに向く
- 役割が違うので、両方組み合わせることで多層防御になる

## ETL の流れの変化

```
STEP 1: Extract → Load
STEP 2: Extract → Validate（Pydantic → Pandera）→ Load
```

## 作成したファイル

### `src/transform/validator.py`

#### Pydantic モデル（行レベル検証）

```python
class OrderRow(BaseModel):
    order_id: str
    quantity: int
    unit_price: int
    order_date: date
    status: Literal["completed", "pending", "cancelled"]
    product_id: str
    ...

    @field_validator("quantity")
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("quantity は 1 以上である必要があります")
        return v
```

- `BaseModel` を継承してクラスを定義するだけで、型チェックが自動で行われる
- `@field_validator` で「型が正しくても値が不正」なケースを追加検証できる
- `Literal["completed", "pending", "cancelled"]` で選択肢を列挙型として制限できる

#### Pandera スキーマ（DataFrame レベル検証）

```python
ORDER_SCHEMA = DataFrameSchema(
    columns={
        "quantity":   Column(int, Check.greater_than(0), nullable=False),
        "status":     Column(str, Check.isin(VALID_STATUSES), nullable=False),
        "order_date": Column("datetime64[ns]", nullable=False),
        ...
    },
    checks=[
        Check(lambda df: df["order_id"].is_unique, error="order_id に重複があります"),
    ],
)
```

- `Column(型, チェック, nullable=False)` で列ごとのルールを定義
- `checks=[]` で「複数列にまたがるチェック」も書ける（例：order_id の一意性）
- `lazy=True` をつけると、最初のエラーで止まらず全エラーをまとめて報告してくれる

#### 検証の2段階フロー

```python
def validate_orders(df: pd.DataFrame) -> pd.DataFrame:
    df = validate_rows_with_pydantic(df)    # エラー行を除外して続行
    df = validate_dataframe_with_pandera(df) # 構造エラーなら例外を送出
    return df
```

## 動作確認

正常データ 1000 件では全件通過：
```
[Validate][Pydantic] 全 1000 件が正常です。
[Validate][Pandera] スキーマ検証 OK（1000 件）
```

壊れたデータを混ぜたテストでは正しくエラー検出：
```
[Validate][Pydantic] エラー行 order_id=ORD-00002: quantity は 1 以上である必要があります（実際の値: 0）
[Validate][Pydantic] エラー行 order_id=ORD-00003: Input should be 'completed', 'pending' or 'cancelled'
[Validate][Pydantic] 2 件のエラー行を除外しました。
```

## 学んだ概念

| 概念 | 説明 |
|---|---|
| Pydantic `BaseModel` | クラスのフィールドに型を書くだけで自動バリデーションが走る |
| `@field_validator` | 型チェック後に追加のカスタムバリデーションを実装するデコレータ |
| `Literal["a", "b"]` | 値を特定の文字列のみに制限する型ヒント |
| Pandera `DataFrameSchema` | DataFrame の列・型・値域を宣言的に定義するスキーマ |
| `lazy=True` | 最初のエラーで止まらず全エラーを収集してから報告する |
| 多層防御 | Pydantic（行）+ Pandera（DataFrame）と役割を分けて検証を重ねる考え方 |

## 次のステップ（STEP 3）での改善点
- 今の検証ロジックにテストがない（手動確認だけ）
- → pytest で「正常データは通る」「壊れたデータは弾かれる」を自動テストにする
