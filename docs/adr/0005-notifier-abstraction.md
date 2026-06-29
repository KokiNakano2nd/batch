# 0005 - 通知レイヤーの抽象化

## ステータス

採用（2026-06-29）

---

## 背景と問題

ETL パイプラインが失敗したとき、運用担当者に通知する必要がある。  
通知先は現時点では Slack を想定しているが、将来メール・PagerDuty などへの変更・追加が考えられる。  
また、開発・テスト環境では実際の Slack 通知なしで動作できることが望ましい。

**判断が必要な問い：**  
通知処理をどう設計すれば、将来の通知先変更に柔軟に対応できるか。

---

## 意思決定の基準

- 通知先を変えるときに、呼び出し側（`pipeline.py`）を変更しなくてよいこと
- 開発環境では Slack へ送らず、ログ出力だけで動作できること
- 新しい通知先（メールなど）を追加するときのコスト（変更箇所）が最小であること

---

## 検討した選択肢

### A. 抽象基底クラス（BaseNotifier）+ ファクトリ関数（採用）

### B. 環境変数の if 分岐を pipeline.py に直書きする

### C. 通知ライブラリ（apprise など）を使う

---

## 決定

**A. `BaseNotifier` 抽象クラスを定義し、`get_notifier()` ファクトリ関数で実装を切り替える設計を採用する。**

```
BaseNotifier（抽象クラス）
  ├── LogNotifier    ← デフォルト実装。JSON を stdout/stderr に出力
  └── SlackNotifier  ← SLACK_WEBHOOK_URL 設定時に自動選択

get_notifier()  ← 環境変数を見て適切な実装を返すファクトリ
```

**呼び出し側（pipeline.py）のコード:**
```python
notifier = get_notifier()          # どの実装かを知らなくてよい
notifier.send(title=..., message=..., level="error")
```

### 採用による良い点

- `pipeline.py` は `BaseNotifier` インターフェースのみを知ればよい（疎結合）
- 新しい通知先は `BaseNotifier` を継承して `send()` を実装するだけで追加できる
- `get_notifier()` に分岐を 1 行追加するだけで切り替えられる
- テスト時は `BaseNotifier` の mock を渡すだけで通知をテストできる

### 採用による懸念点

- 通知先が 1 つしかない時点では過剰設計に見える
- ファイルが複数（`base.py` / `factory.py` / `log_notifier.py` / `slack_notifier.py`）に分かれる

---

## 各選択肢の比較

### A. BaseNotifier + ファクトリ（採用）

**良い点**
- 開放閉鎖原則（Open/Closed Principle）に準拠：既存コードを変更せず機能追加できる
- テスト時に mock を注入しやすい
- 将来 Slack → メール → PagerDuty への拡張が最小コストでできる

**懸念点**
- 抽象クラス・ファクトリパターンの理解が必要（初学者には難解に感じる場合がある）

---

### B. pipeline.py に if 分岐を直書きする

```python
# B 案のイメージ
if os.environ.get("SLACK_WEBHOOK_URL"):
    # Slack に送信するコード
else:
    # ログに出力するコード
```

**良い点**
- ファイル分割なし。シンプルで読みやすい

**懸念点**
- 通知先が増えるたびに `pipeline.py` を変更する必要がある
- `pipeline.py` が「ETL の制御」と「通知処理の実装」の 2 つの責務を持ってしまう
- テスト時に通知処理だけを差し替えることが難しい

---

### C. apprise などの通知ライブラリを使う

**良い点**
- Slack・メール・LINE など 100 以上の通知先が設定ファイルで切り替えられる

**懸念点**
- 外部ライブラリへの依存が増える
- 通知のカスタマイズ（メッセージフォーマットなど）がライブラリの制約を受ける
- 通知が失敗した場合の挙動が外部ライブラリに依存する

---

## ログ出力フォーマット（LogNotifier の仕様）

CloudWatch / Datadog などのログ収集ツールが取り込みやすいよう、JSON 形式で出力する。

```json
{
  "timestamp": "2024-03-15T10:30:00.123456+00:00",
  "level": "ERROR",
  "title": "ETL 失敗: orders-etl-pipeline",
  "message": "Flow Run: run-abc\n状態: ..."
}
```

| level | 出力先 |
|---|---|
| `"error"` | stderr |
| `"warning"` / `"info"` | stdout |

---

## 参考

- 実装: `src/notify/` ディレクトリ一式
- [Python ABC（抽象基底クラス）ドキュメント](https://docs.python.org/ja/3/library/abc.html)
