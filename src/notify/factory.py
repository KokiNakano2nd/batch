import os

from src.notify.base import BaseNotifier
from src.notify.log_notifier import LogNotifier
from src.notify.slack_notifier import SlackNotifier


def get_notifier() -> BaseNotifier:
    """環境変数に応じて通知先を切り替えて返す。

    SLACK_WEBHOOK_URL が設定されていれば SlackNotifier、
    なければ LogNotifier（標準出力への JSON ログ）を返す。

    将来メール通知などを追加する場合も、ここに分岐を1行追加するだけでよい。
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if webhook_url:
        return SlackNotifier(webhook_url)
    return LogNotifier()
