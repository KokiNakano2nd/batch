"""
pipeline.py の単体テスト

Prefect の @task / @flow は、テスト時に「通常の Python 関数」として直接呼び出せる。
そのため、モックを使って DB や CSV への依存を切り離して検証できる。
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pipeline import (
    etl_pipeline,
    extract_task,
    get_watermark_task,
    load_dwh_task,
    load_staging_task,
    on_flow_failure,
    setup_schema_task,
    update_watermark_task,
    validate_task,
)


# ---------------------------------------------------------------------------
# 各タスクの単体テスト
# ---------------------------------------------------------------------------

class TestSetupSchemaTask:
    def test_calls_all_schema_functions(self):
        """setup_schema_task は3つのスキーマ作成関数を呼ぶこと。"""
        mock_engine = MagicMock()
        with (
            patch("pipeline.create_table") as m_ct,
            patch("pipeline.create_watermark_table") as m_wt,
            patch("pipeline.create_dwh_tables") as m_dwh,
        ):
            setup_schema_task(mock_engine)
            m_ct.assert_called_once_with(mock_engine)
            m_wt.assert_called_once_with(mock_engine)
            m_dwh.assert_called_once_with(mock_engine)


class TestGetWatermarkTask:
    def test_returns_none_on_first_run(self):
        """初回（watermark 未登録）は None を返すこと。"""
        mock_engine = MagicMock()
        with patch("pipeline.get_watermark", return_value=None):
            result = get_watermark_task(mock_engine)
        assert result is None

    def test_returns_date_on_subsequent_run(self):
        """2回目以降は登録済みの date を返すこと。"""
        mock_engine = MagicMock()
        expected = date(2024, 6, 1)
        with patch("pipeline.get_watermark", return_value=expected):
            result = get_watermark_task(mock_engine)
        assert result == expected


class TestExtractTask:
    def test_returns_dataframe(self):
        """extract_task は DataFrame を返すこと。"""
        dummy_df = pd.DataFrame([{"order_id": "ORD-00001"}])
        with patch("pipeline.read_orders_csv", return_value=dummy_df):
            result = extract_task("data/orders.csv", since=None)
        assert isinstance(result, pd.DataFrame)

    def test_passes_since_to_reader(self):
        """since を指定すると read_orders_csv に渡されること。"""
        dummy_df = pd.DataFrame()
        since = date(2024, 6, 1)
        with patch("pipeline.read_orders_csv", return_value=dummy_df) as mock_read:
            extract_task("data/orders.csv", since=since)
            mock_read.assert_called_once_with("data/orders.csv", since=since)


class TestValidateTask:
    def test_returns_validated_dataframe(self):
        """validate_task は validate_orders の結果をそのまま返すこと。"""
        input_df = pd.DataFrame([{"order_id": "ORD-00001"}])
        output_df = pd.DataFrame([{"order_id": "ORD-00001", "status": "completed"}])
        with patch("pipeline.validate_orders", return_value=output_df):
            result = validate_task(input_df)
        assert result.equals(output_df)


class TestLoadStagingTask:
    def test_calls_upsert_orders(self):
        """load_staging_task は upsert_orders を呼ぶこと。"""
        mock_engine = MagicMock()
        df = pd.DataFrame([{"order_id": "ORD-00001"}])
        with patch("pipeline.upsert_orders") as mock_upsert:
            load_staging_task(df, mock_engine)
            mock_upsert.assert_called_once_with(df, mock_engine)


class TestLoadDwhTask:
    def test_calls_all_dim_and_fact_loaders(self):
        """load_dwh_task は dim 4 関数をすべて呼ぶこと。"""
        mock_engine = MagicMock()
        with (
            patch("pipeline.upsert_dim_customer") as m_c,
            patch("pipeline.upsert_dim_product") as m_p,
            patch("pipeline.upsert_dim_date") as m_d,
            patch("pipeline.upsert_fact_orders") as m_f,
        ):
            load_dwh_task(mock_engine)
            m_c.assert_called_once_with(mock_engine)
            m_p.assert_called_once_with(mock_engine)
            m_d.assert_called_once_with(mock_engine)
            m_f.assert_called_once_with(mock_engine)


class TestUpdateWatermarkTask:
    def test_calls_update_watermark(self):
        """update_watermark_task は update_watermark を呼ぶこと。"""
        mock_engine = MagicMock()
        new_wm = date(2024, 12, 31)
        with patch("pipeline.update_watermark") as mock_uw:
            update_watermark_task(mock_engine, new_wm)
            mock_uw.assert_called_once()


# ---------------------------------------------------------------------------
# フロー全体の結合テスト
# ---------------------------------------------------------------------------

class TestEtlPipeline:
    def _make_sample_df(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "order_id":      "ORD-00001",
            "customer_id":   "C-0001",
            "customer_name": "田中太郎",
            "product_id":    "P001",
            "product_name":  "ワイヤレスイヤホン",
            "quantity":      2,
            "unit_price":    8800,
            "order_date":    pd.Timestamp("2024-03-15"),
            "status":        "completed",
        }])

    def test_full_flow_runs_without_error(self):
        """全タスクをモックにして、フローがエラーなく完了すること。"""
        df = self._make_sample_df()
        with (
            patch("pipeline.get_engine", return_value=MagicMock()),
            patch("pipeline.create_table"),
            patch("pipeline.create_watermark_table"),
            patch("pipeline.create_dwh_tables"),
            patch("pipeline.get_watermark", return_value=None),
            patch("pipeline.read_orders_csv", return_value=df),
            patch("pipeline.validate_orders", return_value=df),
            patch("pipeline.upsert_orders"),
            patch("pipeline.upsert_dim_customer"),
            patch("pipeline.upsert_dim_product"),
            patch("pipeline.upsert_dim_date"),
            patch("pipeline.upsert_fact_orders"),
            patch("pipeline.update_watermark"),
        ):
            etl_pipeline()  # 例外が出なければ OK

    def test_skips_load_when_no_new_data(self):
        """新規データがない（empty DataFrame）場合は Upsert が呼ばれないこと。"""
        with (
            patch("pipeline.get_engine", return_value=MagicMock()),
            patch("pipeline.create_table"),
            patch("pipeline.create_watermark_table"),
            patch("pipeline.create_dwh_tables"),
            patch("pipeline.get_watermark", return_value=date(2024, 12, 31)),
            patch("pipeline.read_orders_csv", return_value=pd.DataFrame()),
            patch("pipeline.upsert_orders") as mock_upsert,
        ):
            etl_pipeline()
            mock_upsert.assert_not_called()


# ---------------------------------------------------------------------------
# on_failure フックのテスト
# ---------------------------------------------------------------------------

class TestOnFlowFailure:
    def test_calls_notifier_send_on_failure(self):
        """on_flow_failure は get_notifier().send() を呼ぶこと。"""
        mock_notifier = MagicMock()
        mock_flow = MagicMock()
        mock_flow.name = "orders-etl-pipeline"
        mock_flow_run = MagicMock()
        mock_flow_run.name = "test-run"
        mock_state = MagicMock()
        mock_state.message = "Task crashed."

        with patch("pipeline.get_notifier", return_value=mock_notifier):
            on_flow_failure(mock_flow, mock_flow_run, mock_state)

        mock_notifier.send.assert_called_once()
        call_kwargs = mock_notifier.send.call_args
        assert call_kwargs.kwargs["level"] == "error"
        assert "orders-etl-pipeline" in call_kwargs.kwargs["title"]
