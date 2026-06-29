# 0001 - データ処理ライブラリの選定

## ステータス

採用（2026-06-29）

---

## 背景と問題

ETL パイプラインで CSV を読み込み、フィルタリング・集計を行う必要がある。  
Python のデータ処理ライブラリは複数存在し、それぞれ速度・メモリ効率・学習コストが異なる。

**判断が必要な問い：**  
メインパイプラインにどのライブラリを採用するか。大規模データ処理にはどのライブラリを使うか。

---

## 意思決定の基準

- Python 初学者が読める、標準的なコードで書けること
- 小〜中規模データ（数千〜数十万行）で十分な速度が出ること
- 大規模データ（100 万行以上）にも対応できる拡張パスがあること
- 既存のエコシステム（SQLAlchemy / Pandera など）との親和性が高いこと

---

## 検討した選択肢

### A. pandas をメインに採用、大規模データは polars / DuckDB で補完（採用）

### B. polars に統一する

### C. DuckDB に統一する

---

## 決定

**A. pandas をメインパイプラインに採用し、大規模データ処理の選択肢として polars / DuckDB を実装する。**

- `src/extract/reader.py` — pandas 版（メインパイプラインで使用）
- `src/extract/reader_polars.py` — polars 版（大規模データ向けの代替）
- `src/transform/duckdb_aggregator.py` — DuckDB 版（CSV を直接 SQL 集計）

### 採用による良い点

- pandas は Python データ処理の事実上の標準。学習リソースが豊富
- Pandera / SQLAlchemy (`pd.read_sql`) など、周辺ライブラリが pandas を前提としている
- polars・DuckDB も実装しておくことで、データ規模が増えたときに切り替えられる

### 採用による懸念点

- 1 億行を超えるデータでは pandas はメモリ不足になる可能性がある
- 3 種類のライブラリを維持するコストが生じる

---

## 各選択肢の比較

### A. pandas + polars / DuckDB（補完）

**良い点**
- pandas は可読性が高く、初学者が理解しやすい
- Pandera や SQLAlchemy との統合がスムーズ
- polars / DuckDB を並走実装することで速度比較・学習が可能

**懸念点**
- 大規模データで性能限界に達した場合、切り替えコストが発生する

---

### B. polars に統一

**良い点**
- pandas より 3〜5 倍高速（10 万件の増分抽出で実測 4.6 倍差）
- Lazy 評価でメモリ効率が良い
- 大規模データでも同一コードで対応できる

**懸念点**
- `pd.DataFrame` を前提とする Pandera / SQLAlchemy と型が合わない
- `.pl()` / `.to_pandas()` の変換コストと複雑さが増す
- 学習コストが pandas より高い（初学者向けの教材が少ない）

---

### C. DuckDB に統一

**良い点**
- CSV / Parquet を DB サーバーなしで直接 SQL クエリできる
- 集計・フィルタが高速（列指向ストレージ）
- SQL を知っていれば直感的に書ける

**懸念点**
- 行単位の変換・検証（Pydantic による 1 行ずつの型チェック）には向かない
- DuckDB の DataFrame は最終的に pandas / polars に変換する必要がある
- ロード処理（SQLAlchemy + PostgreSQL）との統合が複雑になる

---

## 参考

- [pandas ドキュメント](https://pandas.pydata.org/docs/)
- [polars ドキュメント](https://docs.pola.rs/)
- [DuckDB ドキュメント](https://duckdb.org/docs/)
- プロジェクト内ベンチマーク: `scripts/benchmark.py`（10 万件での実測値）
