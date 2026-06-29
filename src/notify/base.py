from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """通知送信の抽象基底クラス。

    新しい通知先（Slack・メールなど）を追加するときは
    このクラスを継承して send() を実装するだけでよい。
    """

    @abstractmethod
    def send(self, title: str, message: str, level: str = "error") -> None:
        """通知を送信する。

        Args:
            title:   通知のタイトル（例: "ETL 失敗"）
            message: 詳細メッセージ
            level:   重要度。"error" / "warning" / "info" のいずれか
        """
