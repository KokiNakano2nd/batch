# STEP 3 - テスト（pytest）

## 目的
STEP 2 で作ったバリデーションロジックは、手動で壊れたデータを用意して目で確認していた。
これを「自動テスト」に変えることで：
- コードを変更しても「壊れていないか」を瞬時に確認できる
- 「正しく動く」ことをコードで表現できる

## pytest とは

Python の標準的なテストフレームワーク。  
`test_` で始まる関数を自動で検出して実行してくれる。

```bash
.venv/bin/pytest tests/ -v
```

## テストの種類と今回の選択

| 種類 | 内容 | 今回 |
|---|---|---|
| 単体テスト | 関数1つを単独でテスト | ✅ |
| 結合テスト | 複数の処理をつないでテスト | STEP 4 以降 |
| E2E テスト | 最初から最後まで通しでテスト | 将来 |

## 作成したファイル

### `tests/test_reader.py` — Extract のテスト

```python
def test_order_date_is_datetime(sample_csv):
    df = read_orders_csv(sample_csv)
    assert pd.api.types.is_datetime64_any_dtype(df["order_date"])
```

**`tmp_path` fixture（フィクスチャ）**：
pytest が自動で用意してくれるテスト専用の一時ディレクトリ。
テスト関数の引数に `tmp_path` と書くだけで使える。
テスト後に自動で削除されるため、実際のファイルを汚さない。

---

### `tests/test_validator.py` — Transform のテスト

```python
def make_valid_df(**overrides) -> pd.DataFrame:
    base = { "order_id": "ORD-00001", "quantity": 2, ... }
    base.update(overrides)
    return pd.DataFrame([base])
```

`make_valid_df(quantity=0)` のように「1項目だけ壊す」書き方ができる。
これにより各テストが何を検証しているかが明確になる。

テストケース：
- 正常データは通過する
- quantity=0 / マイナスは除外される
- 定義外の status は除外される
- 定義外の product_id は除外される
- 正常行とエラー行が混在 → 正常行だけ残る
- order_id が重複 → Pandera が例外を送出する

---

### `tests/test_writer.py` — Load のテスト（モック使用）

Load は DB に接続するため、テストのたびに PostgreSQL を動かす必要がある。
→ **モック（Mock）** を使って DB を偽物に差し替える。

```python
from unittest.mock import MagicMock, patch

mock_engine = MagicMock()   # 偽の engine
mock_conn = MagicMock()     # 偽の connection
mock_engine.connect.return_value.__enter__.return_value = mock_conn

create_table(mock_engine)

mock_conn.execute.assert_called_once()  # execute が呼ばれたか確認
```

**モックとは**：本物の代わりに使う「偽物オブジェクト」。  
呼ばれたか、何回呼ばれたか、何の引数で呼ばれたかを記録する。
DB なしでも「正しく呼ばれているか」を確認できる。

## 実行方法

```bash
# 全テスト実行
.venv/bin/pytest tests/ -v

# ファイルを指定して実行
.venv/bin/pytest tests/test_validator.py -v

# テスト名を絞って実行（-k でキーワード指定）
.venv/bin/pytest tests/ -k "quantity" -v
```

## 実行結果

```
17 passed in 0.59s
```

## 学んだ概念

| 概念 | 説明 |
|---|---|
| pytest | `test_` 関数を自動検出・実行するテストフレームワーク |
| fixture (`tmp_path`) | テストの前準備を行う仕組み。pytest が自動で提供するものもある |
| `assert` | 「〜であるべき」を表明する。失敗するとテストが落ちる |
| モック (`MagicMock`) | 本物の代わりに使う偽物オブジェクト。DB 等の外部依存を排除できる |
| `patch.object` | 特定のオブジェクトのメソッドをモックに差し替える |
| `assert_called_once()` | モックが1回だけ呼ばれたことを確認する |

## 次のステップ（STEP 4）での改善点
- 今は全件を `if_exists="replace"` で入れ直している（既存データが消える）
- → 増分抽出（前回取り込んだ日時以降だけ取得）＋ Upsert に改善する
