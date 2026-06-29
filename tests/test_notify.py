"""
src/notify/ の単体テスト

LogNotifier / SlackNotifier / factory の動作を検証する。
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.notify.base import BaseNotifier
from src.notify.factory import get_notifier
from src.notify.log_notifier import LogNotifier
from src.notify.slack_notifier import SlackNotifier


# ---------------------------------------------------------------------------
# LogNotifier のテスト
# ---------------------------------------------------------------------------

class TestLogNotifier:
    def test_implements_base_notifier(self):
        """LogNotifier は BaseNotifier のサブクラスであること。"""
        assert issubclass(LogNotifier, BaseNotifier)

    def test_send_outputs_valid_json(self, capsys):
        """send() は JSON 形式で stdout か stderr に出力すること。"""
        notifier = LogNotifier()
        notifier.send(title="テスト", message="テストメッセージ", level="info")

        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["title"] == "テスト"
        assert payload["message"] == "テストメッセージ"
        assert payload["level"] == "INFO"
        assert "timestamp" in payload

    def test_error_level_writes_to_stderr(self, capsys):
        """level="error" のとき stderr に出力されること。"""
        notifier = LogNotifier()
        notifier.send(title="エラー", message="失敗しました", level="error")

        captured = capsys.readouterr()
        payload = json.loads(captured.err.strip())
        assert payload["level"] == "ERROR"

    def test_send_includes_all_required_fields(self, capsys):
        """出力 JSON に timestamp / level / title / message が含まれること。"""
        notifier = LogNotifier()
        notifier.send(title="T", message="M", level="warning")

        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        for key in ("timestamp", "level", "title", "message"):
            assert key in payload


# ---------------------------------------------------------------------------
# SlackNotifier のテスト
# ---------------------------------------------------------------------------

class TestSlackNotifier:
    def test_implements_base_notifier(self):
        """SlackNotifier は BaseNotifier のサブクラスであること。"""
        assert issubclass(SlackNotifier, BaseNotifier)

    def test_send_posts_to_webhook_url(self):
        """send() は Webhook URL に POST リクエストを送ること。"""
        notifier = SlackNotifier("https://hooks.slack.com/test")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            notifier.send(title="テスト", message="成功", level="info")
            mock_open.assert_called_once()

    def test_send_raises_on_non_200(self):
        """Webhook が 200 以外を返したとき RuntimeError を送出すること。"""
        notifier = SlackNotifier("https://hooks.slack.com/test")

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Slack 通知に失敗しました"):
                notifier.send(title="エラー", message="失敗", level="error")


# ---------------------------------------------------------------------------
# factory のテスト
# ---------------------------------------------------------------------------

class TestGetNotifier:
    def test_returns_log_notifier_by_default(self):
        """SLACK_WEBHOOK_URL が未設定のとき LogNotifier を返すこと。"""
        env = {k: v for k, v in os.environ.items() if k != "SLACK_WEBHOOK_URL"}
        with patch.dict(os.environ, env, clear=True):
            notifier = get_notifier()
        assert isinstance(notifier, LogNotifier)

    def test_returns_slack_notifier_when_env_set(self):
        """SLACK_WEBHOOK_URL が設定されているとき SlackNotifier を返すこと。"""
        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            notifier = get_notifier()
        assert isinstance(notifier, SlackNotifier)
