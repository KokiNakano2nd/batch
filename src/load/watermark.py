from datetime import date

from sqlalchemy import text


def create_watermark_table(engine) -> None:
    """watermarks テーブルがなければ作成する。"""
    ddl = """
    CREATE TABLE IF NOT EXISTS watermarks (
        job_name       VARCHAR(100) PRIMARY KEY,
        last_loaded_at DATE NOT NULL
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    print("[Watermark] テーブルを準備しました。")


def get_watermark(engine, job_name: str) -> date | None:
    """job_name に対応する最終取込日を返す。未登録なら None。"""
    sql = "SELECT last_loaded_at FROM watermarks WHERE job_name = :job_name"
    with engine.connect() as conn:
        row = conn.execute(text(sql), {"job_name": job_name}).fetchone()
    return row[0] if row else None


def update_watermark(engine, job_name: str, loaded_at: date) -> None:
    """最終取込日を更新する。未登録なら INSERT、登録済みなら UPDATE。"""
    sql = """
    INSERT INTO watermarks (job_name, last_loaded_at)
    VALUES (:job_name, :loaded_at)
    ON CONFLICT (job_name) DO UPDATE SET last_loaded_at = EXCLUDED.last_loaded_at
    """
    with engine.begin() as conn:
        conn.execute(text(sql), {"job_name": job_name, "loaded_at": loaded_at})
    print(f"[Watermark] {job_name} の最終取込日を {loaded_at} に更新しました。")
