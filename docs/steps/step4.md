# STEP 4 - 増分抽出 + べき等 Upsert

## 目的

毎回全件ロードするのをやめて、「前回以降に新しく入ったデータだけを取り込む」仕組みを作る。
さらに同じデータを何度実行しても DB が壊れない「べき等（idempotent）」な書き込みに切り替える。

---

## やったこと

### 作成・変更したファイル

| ファイル | 内容 |
|---|---|
| `src/load/watermark.py` | 新規作成。最終取込日を管理する `watermarks` テーブルの作成・読み取り・更新を担当。 |
| `src/extract/reader.py` | `since` パラメータを追加。指定日より新しい行だけ返す増分抽出ロジックを実装。 |
| `src/load/writer.py` | `upsert_orders` 関数を追加。`INSERT ON CONFLICT DO UPDATE` でべき等な書き込みを実現。 |
| `main.py` | watermark を取得 → 増分抽出 → 検証 → Upsert → watermark 更新、という新しいフローに変更。 |
| `tests/test_watermark.py` | 新規作成。watermark の CRUD をモックで検証（6件）。 |
| `tests/test_reader.py` | 増分抽出テスト3件を追加（since フィルタ、全件、空返し）。 |
| `tests/test_writer.py` | `upsert_orders` のテスト3件を追加（SQL実行・commit・records の型）。 |

---

## 学んだ概念

### Watermark（ウォーターマーク）
「ここまで処理した」という目印（=最終取込日）を DB に記録しておく仕組み。
次回実行時にこの日付以降のデータだけを取得することで、全件スキャンを避けられる。

```
watermarks テーブル
┌─────────────┬───────────────┐
│ job_name    │ last_loaded_at│
├─────────────┼───────────────┤
│ orders_etl  │ 2024-12-31    │
└─────────────┴───────────────┘
```

### 増分抽出（Incremental Extract）
前回の watermark より新しい行だけを取り出すこと。
データ量が増えても処理時間が増えにくいため、本番バッチでは全件ロードより圧倒的に使われる。

```python
# since=2024-06-01 なら 2024-06-02 以降の行だけが返る
df = df[df["order_date"].dt.date > since]
```

### べき等（Idempotent）
「何回実行しても同じ結果になる」という性質。
バッチ処理は失敗して再実行することがよくあるため、重複や矛盾が起きないべき等設計が重要。

STEP 1 の `if_exists="replace"` はテーブルを丸ごと作り直すので非べき等だった。
STEP 4 の Upsert は同じ order_id を何度挿入しても上書きになるのでべき等。

### INSERT ON CONFLICT DO UPDATE（Upsert）
PostgreSQL の構文で「INSERT を試みて、主キーが衝突したら UPDATE する」という動作をする。

```sql
INSERT INTO orders (order_id, ...) VALUES (:order_id, ...)
ON CONFLICT (order_id) DO UPDATE SET
    status = EXCLUDED.status,
    ...
```

`EXCLUDED` は「今まさに INSERT しようとしていた行」を参照するキーワード。

---

## 次のステップでの改善点

- 現状は `order_date`（日付）を watermark にしているが、注文日は「受注した日」なので
  過去日付の修正データが来ると取りこぼす可能性がある。
  本番では `updated_at`（更新タイムスタンプ）を watermark にするのが一般的。
- orders テーブルは依然フラットな1枚テーブル。STEP 5 でディメンショナルモデリング（星型スキーマ）に分割する。
