# 結婚式準備管理システム

辰巳裕亮 & 陳瑞芳 - 2027/01/31（日）挙式に向けた準備管理・ログシステム

## セットアップ

```bash
# 基本（必須）
pip install pyyaml

# スプレッドシート同期（オプション）
pip install gspread google-auth
```

## 使い方

```bash
# 残日数・進捗サマリー
python3 wedding/wedding.py status

# タスク一覧
python3 wedding/wedding.py tasks
python3 wedding/wedding.py tasks --phase phase_01      # フェーズ指定
python3 wedding/wedding.py tasks --status not_started   # ステータス指定
python3 wedding/wedding.py tasks --overdue              # 期限超過のみ

# タスクステータス更新
python3 wedding/wedding.py update --id t001 --status done

# リマインダー（デフォルト: 14日以内）
python3 wedding/wedding.py remind
python3 wedding/wedding.py remind --days 30

# 会場連絡先
python3 wedding/wedding.py contact

# ゲストリスト
python3 wedding/wedding.py guests
python3 wedding/wedding.py guests --list

# 予算管理
python3 wedding/wedding.py budget

# ログ記録
python3 wedding/wedding.py log -m "プランナーと打ち合わせ" -n "次回は5月中旬"
```

## ファイル構成

| ファイル | 内容 |
|---------|------|
| `config.yaml` | 挙式情報・会場連絡先・カップル情報 |
| `tasks.yaml` | タスク一覧（7フェーズ・33タスク） |
| `guests.yaml` | ゲストリスト |
| `budget.yaml` | 見積もり・予算管理 |
| `wedding.py` | メインCLI |
| `sheets_sync.py` | スプレッドシート同期 |
| `logs/` | 月別活動ログ |

## スプレッドシート同期

タスク・ゲスト・予算データをGoogle Sheetsと双方向同期できます。

### 初回セットアップ

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. Google Sheets API を有効化
3. サービスアカウントを作成し、JSONキーをダウンロード
4. JSONキーを `wedding/credentials.json` に配置
5. [スプレッドシート](https://docs.google.com/spreadsheets/d/1fhpPLRTrN6tUwA-f4XhTFLJZ2hYcFPSQOXth1Jx5cBU/) をサービスアカウントのメールアドレスに共有（編集者権限）

### 使い方

```bash
# 同期状態を確認
python3 wedding/sheets_sync.py status

# YAML → スプレッドシートへ書き込み
python3 wedding/sheets_sync.py push           # 全データ
python3 wedding/sheets_sync.py push tasks     # タスクのみ
python3 wedding/sheets_sync.py push guests    # ゲストのみ
python3 wedding/sheets_sync.py push budget    # 予算のみ

# スプレッドシート → YAMLへ取り込み
python3 wedding/sheets_sync.py pull           # 全データ
python3 wedding/sheets_sync.py pull tasks     # タスクのみ
```

### 同期の流れ

1. `push` でYAMLデータをシートに書き込み（初回はシート自動作成）
2. スプレッドシート上で編集（ステータス変更、ゲスト追加、金額入力等）
3. `pull` でシートの変更をYAMLに取り込み
4. `git commit` でバージョン管理

## Google Calendar連携

全タスクの期限がGoogle Calendar（yusuke0516z@gmail.com）に登録済み。
優先度別に色分け: 赤=high / ピンク=medium / 黄=low

## タスクステータス

| ステータス | 意味 |
|-----------|------|
| `not_started` | 未着手 |
| `in_progress` | 進行中 |
| `done` | 完了 |
| `skipped` | スキップ |

## 会場連絡先

- TEL: 045-470-7470
- Mail: AQY@One-Heart.info
- 件名: 1/31 辰巳家 陳家 担当：〇〇宛て
- 営業: 平日12:00-18:00 / 土日祝9:00-19:00
- 休館: 月・火（祝日除く）
- 打ち合わせは原則平日営業時間内
