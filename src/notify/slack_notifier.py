import json
import urllib.request

from src.notify.base import BaseNotifier


class SlackNotifier(BaseNotifier):
    """Slack Incoming Webhook へ通知を送る実装。

    使い方:
        1. Slack の「Incoming Webhooks」アプリで Webhook URL を発行する
        2. 環境変数 SLACK_WEBHOOK_URL に設定する
        3. factory.py が自動的にこのクラスを使うようになる

    参考: https://api.slack.com/messaging/webhooks
    """

    LEVEL_EMOJI = {
        "error":   ":red_circle:",
        "warning": ":large_yellow_circle:",
        "info":    ":large_green_circle:",
    }

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    def send(self, title: str, message: str, level: str = "error") -> None:
        emoji = self.LEVEL_EMOJI.get(level, ":white_circle:")
        text = f"{emoji} *{title}*\n{message}"
        payload = json.dumps({"text": text}).encode("utf-8")

        req = urllib.request.Request(
            self._webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Slack 通知に失敗しました: HTTP {resp.status}")
