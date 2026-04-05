# 結婚式準備管理システム

辰巳裕亮 & 陳瑞芳 - 2027/01/31（日）挙式に向けた準備管理・ログシステム

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

# ログ記録
python3 wedding/wedding.py log -m "プランナーと打ち合わせ" -n "次回は5月中旬"
```

## ファイル構成

| ファイル | 内容 |
|---------|------|
| `config.yaml` | 挙式情報・会場連絡先・カップル情報 |
| `tasks.yaml` | タスク一覧（7フェーズ） |
| `wedding.py` | メインCLI |
| `logs/` | 月別活動ログ |

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
