# STEP 9-A - Airflow への移植・設計思想の比較

## 目的

Prefect で実装済みの ETL を Apache Airflow に移植する。
同じ処理を2つのツールで書き直すことで、設計思想の違いを体感レベルで理解する。

---

## やったこと

### 作成・変更したファイル

| ファイル | 内容 |
|---|---|
| `docker-compose.airflow.yml` | 新規作成。Airflow 専用の環境（postgres / init / webserver / scheduler）。 |
| `dags/orders_etl_dag.py` | 新規作成。pipeline.py と同じ ETL を Airflow DAG として実装。 |
| `docs/airflow_vs_prefect.md` | 新規作成。Prefect との設計思想・コード比較ドキュメント。 |
| `src/load/writer.py` | `engine.connect()` + `conn.commit()` → `engine.begin()` に変更。 |
| `src/load/watermark.py` | 同上。 |
| `src/load/dwh_loader.py` | 同上。 |
| `tests/test_writer.py` | モックを `begin()` に対応、`test_commits` → `test_uses_transaction` に変更。 |
| `tests/test_watermark.py` | 同上。 |
| `tests/test_dwh_loader.py` | 同上。 |

### Airflow 起動・確認手順

```bash
# STEP 8 の postgres が起動していること（batch_network が必要）
docker compose up -d

# Airflow 環境を起動（初回は pip install が走るため数分かかる）
docker compose -f docker-compose.airflow.yml up -d

# UI: http://localhost:8080  (admin / admin)

# DAG を手動実行
docker compose -f docker-compose.airflow.yml exec airflow-scheduler \
  airflow dags trigger orders_etl

# 全タスクの状態を確認
docker compose -f docker-compose.airflow.yml exec airflow-scheduler \
  airflow tasks states-for-dag-run orders_etl <run_id>

# 停止
docker compose -f docker-compose.airflow.yml down
```

### DAG のタスクグラフ

```
setup_schema → get_watermark → extract → validate → load_staging
                                                          ↓
                                          load_dwh → update_watermark
```

---

## 学んだ概念

### DAG（有向非巡回グラフ）

Airflow の最重要概念。タスクとその依存関係を「グラフ」として表現する。

```
A → B → C   # A が終わったら B、B が終わったら C
     ↓
     D       # B が終わったら D も並行実行できる
```

「非巡回」= ループしない。A → B → A のような循環はできない。

### XCom（クロスコミュニケーション）

タスク間でデータを受け渡す仕組み。DB に保存されるため **JSON シリアライズ可能なデータのみ**。

```python
@task
def extract():
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")  # JSON にして XCom に保存

@task
def validate(records: list[dict]):
    df = pd.DataFrame(records)           # XCom から取り出して DataFrame に戻す
```

DataFrame をそのまま渡せる Prefect との大きな違い。

### >> 演算子

```python
schema_done >> last_loaded   # schema_done の後に last_loaded を実行する
```

引数渡しでは表現できない「実行順序だけの制約」を明示するために使う。

### `engine.begin()` と SQLAlchemy バージョン互換性

```python
# SQLAlchemy 1.4 / 2.x 両方で動く書き方
with engine.begin() as conn:
    conn.execute(text(sql))
    # 自動コミット（context 正常終了時）/ 自動ロールバック（例外時）

# SQLAlchemy 2.x のみ
with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()  # 1.4 にはこのメソッドがない
```

Airflow 2.10.0 の内部では SQLAlchemy 1.4.x が使われているため、
`engine.begin()` パターンに統一することで両環境で動くコードになった。

---

## 次のステップ

- STEP 9-B: polars / DuckDB を使った大規模データのチャンク処理
