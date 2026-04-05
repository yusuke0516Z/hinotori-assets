#!/usr/bin/env python3
"""Google Sheets同期スクリプト - 結婚準備管理

tasks.yaml / guests.yaml / budget.yaml ⟷ スプレッドシート の双方向同期

使い方:
  python3 wedding/sheets_sync.py push          # YAML → シートへ書き込み（全データ）
  python3 wedding/sheets_sync.py push tasks     # タスクのみ
  python3 wedding/sheets_sync.py push guests    # ゲストのみ
  python3 wedding/sheets_sync.py push budget    # 予算のみ
  python3 wedding/sheets_sync.py pull           # シート → YAMLへ取り込み（全データ）
  python3 wedding/sheets_sync.py pull tasks     # タスクのみ
  python3 wedding/sheets_sync.py pull guests    # ゲストのみ
  python3 wedding/sheets_sync.py pull budget    # 予算のみ
  python3 wedding/sheets_sync.py status         # 同期状態を確認

セットアップ:
  1. pip install gspread google-auth
  2. Google Cloud Console でサービスアカウント作成
  3. JSONキーを wedding/credentials.json に配置
  4. スプレッドシートをサービスアカウントのメールアドレスに共有
"""

import argparse
import sys
from datetime import date
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("必要なパッケージをインストールしてください:")
    print("  pip install gspread google-auth")
    sys.exit(1)

import yaml

BASE_DIR = Path(__file__).parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"

# スプレッドシートのシート名マッピング
SHEET_TASKS = "タスク一覧"
SHEET_GUESTS = "招待客リスト"
SHEET_BUDGET = "見積シミュレーター"


# ─────────────────────────────────────────────
# YAML読み書き
# ─────────────────────────────────────────────

def load_yaml(filename):
    with open(BASE_DIR / filename, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(filename, data):
    with open(BASE_DIR / filename, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_config():
    return load_yaml("config.yaml")


# ─────────────────────────────────────────────
# Google Sheets接続
# ─────────────────────────────────────────────

def get_client():
    """gspreadクライアントを取得"""
    if not CREDENTIALS_FILE.exists():
        print(f"エラー: 認証ファイルが見つかりません: {CREDENTIALS_FILE}")
        print()
        print("セットアップ手順:")
        print("  1. Google Cloud Console (https://console.cloud.google.com/) にアクセス")
        print("  2. プロジェクトを作成し、Google Sheets API を有効化")
        print("  3. サービスアカウントを作成し、JSONキーをダウンロード")
        print(f"  4. JSONキーを {CREDENTIALS_FILE} に配置")
        print("  5. スプレッドシートをサービスアカウントのメールアドレスに共有（編集者権限）")
        sys.exit(1)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=scopes)
    return gspread.authorize(creds)


def get_spreadsheet(client):
    """設定ファイルからスプレッドシートを取得"""
    config = load_config()
    spreadsheet_id = config.get("spreadsheet", {}).get("id", "")
    if not spreadsheet_id:
        print("エラー: config.yaml に spreadsheet.id が設定されていません")
        sys.exit(1)
    return client.open_by_key(spreadsheet_id)


def get_or_create_sheet(spreadsheet, title, headers):
    """シートを取得、なければ作成してヘッダーを設定"""
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=100, cols=len(headers))
        ws.update("A1", [headers])
        ws.format("A1:Z1", {"textFormat": {"bold": True}})
        print(f"  シート '{title}' を新規作成しました")
    return ws


# ─────────────────────────────────────────────
# タスク同期
# ─────────────────────────────────────────────

TASK_HEADERS = ["タスクID", "フェーズ", "タスク名", "ステータス", "優先度", "期限日", "メモ", "完了日"]


def push_tasks(spreadsheet):
    """tasks.yaml → シートへ書き込み"""
    tasks_data = load_yaml("tasks.yaml")
    ws = get_or_create_sheet(spreadsheet, SHEET_TASKS, TASK_HEADERS)

    rows = [TASK_HEADERS]
    for phase in tasks_data["phases"]:
        for t in phase["tasks"]:
            rows.append([
                t["id"],
                phase["name"],
                t["title"],
                t["status"],
                t["priority"],
                t.get("due_date", ""),
                t.get("notes", ""),
                t.get("completed_date") or "",
            ])

    ws.clear()
    ws.update("A1", rows)
    ws.format("A1:H1", {"textFormat": {"bold": True}})
    print(f"  タスク: {len(rows) - 1}件をシートに書き込みました")


def pull_tasks(spreadsheet):
    """シート → tasks.yaml へ取り込み"""
    try:
        ws = spreadsheet.worksheet(SHEET_TASKS)
    except gspread.WorksheetNotFound:
        print(f"  エラー: シート '{SHEET_TASKS}' が見つかりません。先に push してください")
        return

    records = ws.get_all_records()
    if not records:
        print("  タスクデータが空です")
        return

    tasks_data = load_yaml("tasks.yaml")

    # シートのデータでtasks.yamlを更新
    sheet_tasks = {r["タスクID"]: r for r in records}
    updated = 0
    for phase in tasks_data["phases"]:
        for task in phase["tasks"]:
            if task["id"] in sheet_tasks:
                r = sheet_tasks[task["id"]]
                changed = False
                if r["ステータス"] and r["ステータス"] != task["status"]:
                    task["status"] = r["ステータス"]
                    changed = True
                if r["メモ"] != (task.get("notes") or ""):
                    task["notes"] = r["メモ"]
                    changed = True
                if r["完了日"] and r["完了日"] != (task.get("completed_date") or ""):
                    task["completed_date"] = r["完了日"]
                    changed = True
                if r["期限日"] and r["期限日"] != (task.get("due_date") or ""):
                    task["due_date"] = r["期限日"]
                    changed = True
                if r["優先度"] and r["優先度"] != task.get("priority", ""):
                    task["priority"] = r["優先度"]
                    changed = True
                if changed:
                    updated += 1

    save_yaml("tasks.yaml", tasks_data)
    print(f"  タスク: {updated}件を更新しました")


# ─────────────────────────────────────────────
# ゲスト同期
# ─────────────────────────────────────────────

GUEST_HEADERS = ["名前", "ふりがな", "側", "関係", "出欠", "アレルギー", "メモ"]


def push_guests(spreadsheet):
    """guests.yaml → シートへ書き込み"""
    guests_data = load_yaml("guests.yaml")
    guests = guests_data.get("guests") or []
    ws = get_or_create_sheet(spreadsheet, SHEET_GUESTS, GUEST_HEADERS)

    side_map = {"groom": "新郎", "bride": "新婦"}
    att_map = {"pending": "未回答", "attending": "出席", "declined": "欠席"}

    rows = [GUEST_HEADERS]
    for g in guests:
        rows.append([
            g.get("name", ""),
            g.get("furigana", ""),
            side_map.get(g.get("side", ""), g.get("side", "")),
            g.get("relation", ""),
            att_map.get(g.get("attendance", ""), g.get("attendance", "")),
            g.get("allergy", ""),
            g.get("notes", ""),
        ])

    ws.clear()
    ws.update("A1", rows)
    ws.format("A1:G1", {"textFormat": {"bold": True}})
    print(f"  ゲスト: {len(rows) - 1}件をシートに書き込みました")


def pull_guests(spreadsheet):
    """シート → guests.yaml へ取り込み"""
    try:
        ws = spreadsheet.worksheet(SHEET_GUESTS)
    except gspread.WorksheetNotFound:
        print(f"  エラー: シート '{SHEET_GUESTS}' が見つかりません。先に push してください")
        return

    records = ws.get_all_records()

    side_map = {"新郎": "groom", "新婦": "bride"}
    att_map = {"未回答": "pending", "出席": "attending", "欠席": "declined"}

    guests = []
    for r in records:
        if not r.get("名前"):
            continue
        guests.append({
            "name": r["名前"],
            "furigana": r.get("ふりがな", ""),
            "side": side_map.get(r.get("側", ""), r.get("側", "")),
            "relation": r.get("関係", ""),
            "attendance": att_map.get(r.get("出欠", ""), r.get("出欠", "")),
            "allergy": r.get("アレルギー", ""),
            "notes": r.get("メモ", ""),
        })

    save_yaml("guests.yaml", {"guests": guests})
    print(f"  ゲスト: {len(guests)}件を取り込みました")


# ─────────────────────────────────────────────
# 予算同期
# ─────────────────────────────────────────────

BUDGET_HEADERS = ["カテゴリ", "項目", "見積額", "実費", "ステータス", "メモ"]


def push_budget(spreadsheet):
    """budget.yaml → シートへ書き込み"""
    budget_data = load_yaml("budget.yaml")
    ws = get_or_create_sheet(spreadsheet, SHEET_BUDGET, BUDGET_HEADERS)

    status_map = {"unpaid": "未払い", "paid": "支払済み", "partial": "一部支払"}

    rows = [BUDGET_HEADERS]

    # 予算上限行
    total = budget_data["budget"].get("total_budget")
    rows.append(["予算上限", "", total or "", "", "", ""])

    for cat in budget_data["categories"]:
        for item in cat["items"]:
            rows.append([
                cat["name"],
                item["name"],
                item.get("estimated") or "",
                item.get("actual") or "",
                status_map.get(item.get("status", ""), item.get("status", "")),
                item.get("notes", ""),
            ])

    ws.clear()
    ws.update("A1", rows)
    ws.format("A1:F1", {"textFormat": {"bold": True}})
    print(f"  予算: {len(rows) - 2}項目をシートに書き込みました")


def pull_budget(spreadsheet):
    """シート → budget.yaml へ取り込み"""
    try:
        ws = spreadsheet.worksheet(SHEET_BUDGET)
    except gspread.WorksheetNotFound:
        print(f"  エラー: シート '{SHEET_BUDGET}' が見つかりません。先に push してください")
        return

    records = ws.get_all_records()
    if not records:
        print("  予算データが空です")
        return

    status_map = {"未払い": "unpaid", "支払済み": "paid", "一部支払": "partial"}

    budget_data = load_yaml("budget.yaml")

    # 予算上限の取り込み
    for r in records:
        if r.get("カテゴリ") == "予算上限":
            val = r.get("見積額", "")
            budget_data["budget"]["total_budget"] = int(val) if val else None
            break

    # 各カテゴリ・項目を更新
    updated = 0
    for cat in budget_data["categories"]:
        for item in cat["items"]:
            for r in records:
                if r.get("カテゴリ") == cat["name"] and r.get("項目") == item["name"]:
                    changed = False
                    est = r.get("見積額", "")
                    if est != "" and est != (item.get("estimated") or ""):
                        item["estimated"] = int(est) if est else None
                        changed = True
                    act = r.get("実費", "")
                    if act != "" and act != (item.get("actual") or ""):
                        item["actual"] = int(act) if act else None
                        changed = True
                    st = r.get("ステータス", "")
                    mapped_st = status_map.get(st, st)
                    if mapped_st and mapped_st != item.get("status", ""):
                        item["status"] = mapped_st
                        changed = True
                    notes = r.get("メモ", "")
                    if notes != (item.get("notes") or ""):
                        item["notes"] = notes
                        changed = True
                    if changed:
                        updated += 1
                    break

    save_yaml("budget.yaml", budget_data)
    print(f"  予算: {updated}項目を更新しました")


# ─────────────────────────────────────────────
# コマンド
# ─────────────────────────────────────────────

TARGETS = {
    "tasks": (push_tasks, pull_tasks),
    "guests": (push_guests, pull_guests),
    "budget": (push_budget, pull_budget),
}


def cmd_push(args):
    """YAML → シートへ書き込み"""
    client = get_client()
    ss = get_spreadsheet(client)
    targets = [args.target] if args.target else list(TARGETS.keys())

    print(f"Push: YAML → スプレッドシート")
    for target in targets:
        push_fn, _ = TARGETS[target]
        push_fn(ss)
    print("完了")


def cmd_pull(args):
    """シート → YAML へ取り込み"""
    client = get_client()
    ss = get_spreadsheet(client)
    targets = [args.target] if args.target else list(TARGETS.keys())

    print(f"Pull: スプレッドシート → YAML")
    for target in targets:
        _, pull_fn = TARGETS[target]
        pull_fn(ss)
    print("完了")


def cmd_status(_args):
    """同期状態を確認"""
    config = load_config()
    ss_config = config.get("spreadsheet", {})

    print("=" * 45)
    print("  スプレッドシート同期状態")
    print("=" * 45)

    if not ss_config.get("id"):
        print("  スプレッドシートID: 未設定")
        print("  config.yaml に spreadsheet.id を設定してください")
        return

    print(f"  スプレッドシートID: {ss_config['id']}")
    if ss_config.get("url"):
        print(f"  URL: {ss_config['url']}")
    print()

    # 認証ファイルの確認
    if CREDENTIALS_FILE.exists():
        print(f"  認証ファイル: OK ({CREDENTIALS_FILE.name})")
    else:
        print(f"  認証ファイル: 未配置")
        print(f"    -> {CREDENTIALS_FILE} に配置してください")
        return

    # 接続テスト
    try:
        client = get_client()
        ss = get_spreadsheet(client)
        print(f"  接続: OK")
        print(f"  シート名: {ss.title}")
        sheets = [ws.title for ws in ss.worksheets()]
        print(f"  シート一覧: {', '.join(sheets)}")

        for name, label in [(SHEET_TASKS, "タスク"), (SHEET_GUESTS, "ゲスト"), (SHEET_BUDGET, "予算")]:
            if name in sheets:
                print(f"    {label}シート: 存在")
            else:
                print(f"    {label}シート: 未作成（pushで自動作成されます）")
    except Exception as e:
        print(f"  接続エラー: {e}")


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Google Sheets同期")
    sub = parser.add_subparsers(dest="command")

    p_push = sub.add_parser("push", help="YAML → シートへ書き込み")
    p_push.add_argument("target", nargs="?", choices=["tasks", "guests", "budget"],
                        help="同期対象（省略時は全データ）")

    p_pull = sub.add_parser("pull", help="シート → YAMLへ取り込み")
    p_pull.add_argument("target", nargs="?", choices=["tasks", "guests", "budget"],
                        help="同期対象（省略時は全データ）")

    sub.add_parser("status", help="同期状態を確認")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    {"push": cmd_push, "pull": cmd_pull, "status": cmd_status}[args.command](args)


if __name__ == "__main__":
    main()
