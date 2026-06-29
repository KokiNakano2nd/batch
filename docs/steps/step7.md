# STEP 7 - 監視・アラート

## 目的

ETL パイプラインが失敗したとき、担当者が気づけるようにする。
また、将来 Slack・メールなど通知先を追加しても `pipeline.py` 側を変更しなくて済む
拡張可能な設計を作る。

---

## やったこと

### 作成・変更したファイル

| ファイル | 内容 |
|---|---|
| `src/notify/base.py` | 新規作成。通知送信の抽象基底クラス `BaseNotifier` を定義。 |
| `src/notify/log_notifier.py` | 新規作成。JSON 構造化ログを出力する `LogNotifier` を実装。 |
| `src/notify/slack_notifier.py` | 新規作成。将来用 `SlackNotifier` スタブ。Webhook URL があれば動く。 |
| `src/notify/factory.py` | 新規作成。環境変数 `SLACK_WEBHOOK_URL` で通知先を切り替える Factory 関数。 |
| `pipeline.py` | `on_flow_failure` フック関数を追加。`@flow` の `on_failure` に登録。 |
| `tests/test_notify.py` | 新規作成。Notifier 系のテスト 9 件。 |
| `tests/test_pipeline.py` | `on_flow_failure` フックのテスト 1 件を追加。 |

### 通知先の切り替え構造

```
src/notify/
  base.py          ← BaseNotifier（抽象クラス）
  log_notifier.py  ← 今回の実装（JSON ログ）
  slack_notifier.py← 将来用（Webhook POST）
  factory.py       ← 環境変数で切り替える
```

Slack を使いたくなったら以下だけで動く:

```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz
python pipeline.py
```

### Prefect の on_failure フック

```python
def on_flow_failure(flow, flow_run, state) -> None:
    notifier = get_notifier()
    notifier.send(title=f"ETL 失敗: {flow.name}", message=..., level="error")

@flow(on_failure=[on_flow_failure])
def etl_pipeline():
    ...
```

フローが失敗（タスクが全リトライを使い切るなど）すると `on_flow_failure` が自動で呼ばれる。

---

## 学んだ概念

### 抽象クラス（ABC）

```python
from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    @abstractmethod
    def send(self, title: str, message: str, level: str) -> None:
        ...
```

- `ABC` を継承したクラスは「設計図」の役割を持つ
- `@abstractmethod` を付けたメソッドはサブクラスで必ず実装しなければならない
- `BaseNotifier()` を直接インスタンス化しようとするとエラーになる

### Factory パターン

```python
def get_notifier() -> BaseNotifier:
    if os.environ.get("SLACK_WEBHOOK_URL"):
        return SlackNotifier(...)
    return LogNotifier()
```

「どのクラスを使うか」の決定を1箇所に集める設計。
呼び出し側（`pipeline.py`）は `get_notifier()` を呼ぶだけでよく、
通知先が変わっても `pipeline.py` を一切触らなくてよい。

### 構造化ログ（JSON ログ）

```json
{"timestamp": "2026-06-29T10:00:00+00:00", "level": "ERROR", "title": "ETL 失敗", "message": "..."}
```

テキストログと違い、1行 = 1イベントなので CloudWatch / Datadog などの
ログ収集ツールが自動でパース・集計できる。
本番システムでは JSON ログがデファクトスタンダード。

### Prefect の on_failure フック

| フック引数 | 型 | 内容 |
|---|---|---|
| `flow` | `Flow` | フローオブジェクト。`flow.name` でフロー名を取れる |
| `flow_run` | `FlowRun` | 実行インスタンス。`flow_run.name` で実行名を取れる |
| `state` | `State` | 最終状態。`state.message` でエラーメッセージを取れる |

---

## 次のステップでの改善点

- 現在は `on_failure` のみ。`on_completion` / `on_cancellation` フックも同様に追加できる。
- `LogNotifier` は stderr に出力するだけ。STEP 8 で Docker Compose に組み込む際に
  ファイルへのログ書き出し（`RotatingFileHandler`）に切り替えるとログが永続化される。
- `SlackNotifier` は実際の Webhook URL があればそのまま動く。
  `SLACK_WEBHOOK_URL` を `.env` ファイルで管理する構成にすると本番運用しやすい。
