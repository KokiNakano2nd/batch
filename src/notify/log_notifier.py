import json
import logging
import sys
from datetime import datetime, timezone

from src.notify.base import BaseNotifier

logger = logging.getLogger(__name__)


class LogNotifier(BaseNotifier):
    """標準出力に JSON 形式で通知を出力する実装。

    将来 Slack や メールに切り替えるまでのデフォルト実装。
    JSON 形式にしておくことで CloudWatch / Datadog などのログ収集ツールが
    そのまま取り込める。
    """

    def send(self, title: str, message: str, level: str = "error") -> None:
        payload = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": level.upper(),
            "title": title,
            "message": message,
        }
        log_line = json.dumps(payload, ensure_ascii=False)

        if level == "error":
            logger.error(log_line)
        elif level == "warning":
            logger.warning(log_line)
        else:
            logger.info(log_line)

        print(log_line, file=sys.stderr if level == "error" else sys.stdout)
