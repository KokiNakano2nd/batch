# GitHub Flow 運用ルール

## ブランチ戦略

このプロジェクトは **GitHub Flow** を採用する。

```
main（本番相当・保護済み）
 │
 ├── feature/add-validation   ─┐
 ├── fix/csv-keyerror          ├─ 作業ブランチ → PR → main にマージ
 └── docs/update-readme       ─┘
```

### 基本フロー

```
1. main から作業ブランチを作る
        │
        ▼
2. ブランチ上で実装・コミット
        │
        ▼
3. GitHub に push
        │
        ▼
4. Pull Request を作成（テンプレートに沿って記載）
        │
        ▼
5. CI（GitHub Actions）が自動でテストを実行
        │
        ▼
6. PR をマージ → main に反映
        │
        ▼
7. 作業ブランチを削除
```

---

## ブランチ命名規則

| 種別 | 命名規則 | 例 |
|---|---|---|
| 機能追加 | `feature/説明` | `feature/add-validation` |
| バグ修正 | `fix/説明` | `fix/csv-keyerror` |
| ドキュメント | `docs/説明` | `docs/update-readme` |
| CI・設定 | `ci/説明` | `ci/add-pytest-action` |

- 説明部分は **英語・ハイフン区切り** で書く
- 長くなりすぎない（3単語程度まで）

---

## Branch Protection Rules（main ブランチ）

`main` には以下の保護ルールを設定済み。

| ルール | 設定 | 理由 |
|---|---|---|
| PR 必須 | ✅ | 直接 push を禁止し、変更履歴を PR に残す |
| 強制 push 禁止 | ✅ | 履歴の書き換えを防ぐ |
| ブランチ削除禁止 | ✅ | `main` の誤削除を防ぐ |
| 会話解決必須 | ✅ | コメントが残ったままマージさせない |

---

## PR の作成ルール

- PR タイトルは **`[種別] 内容`** の形式にする
  - 例: `[Feature] 増分抽出ロジックの追加`
  - 例: `[Fix] CSV 読み込み時の KeyError 修正`
- PR テンプレート（`.github/pull_request_template.md`）に沿って記載する
- 関連 Issue がある場合は本文に `Closes #N` を記載する（マージ時に自動クローズ）

---

## Issue との連携

```
Issue #5「CSV 読み込みでエラー」を作成
        │
        ▼
fix/csv-keyerror ブランチを作成
        │
        ▼
修正 → PR 作成（本文に「Closes #5」を記載）
        │
        ▼
PR マージ → Issue #5 が自動クローズ → Project のステータスも更新
```
