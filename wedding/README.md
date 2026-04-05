# 結婚式準備管理システム

2027/01/31（日）挙式に向けた準備管理・ログシステム

## セットアップ

```bash
pip install pyyaml
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

## Google Calendar連携

タスクの期限をGoogleカレンダーに自動登録できます。

### セットアップ

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. Google Calendar API を有効化
3. OAuth 2.0 クライアントID作成（デスクトップアプリ）
4. 認証情報JSONを `wedding/credentials.json` として配置
5. パッケージインストール:
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

### 使い方

```bash
# 全タスクをカレンダーに同期
python3 wedding/calendar_sync.py sync

# 個別タスクを追加
python3 wedding/calendar_sync.py add --id t002

# 同期済みイベントをクリア
python3 wedding/calendar_sync.py clear
```

## ファイル構成

| ファイル | 内容 |
|---------|------|
| `config.yaml` | 挙式情報・会場連絡先 |
| `tasks.yaml` | タスク一覧（7フェーズ） |
| `guests.yaml` | ゲストリスト |
| `budget.yaml` | 見積もり・予算管理 |
| `wedding.py` | メインCLI |
| `calendar_sync.py` | Google Calendar連携 |
| `logs/` | 月別活動ログ |

## 会場連絡先

- TEL: 045-470-7470
- Mail: AQY@One-Heart.info
- 営業: 平日12:00-18:00 / 土日祝9:00-19:00
- 休館: 月・火（祝日除く）
- 打ち合わせは原則平日営業時間内

## スプレッドシート

[結婚式準備_プロジェクト管理](https://docs.google.com/spreadsheets/d/1fhpPLRTrN6tUwA-f4XhTFLJZ2hYcFPSQOXth1Jx5cBU/)
