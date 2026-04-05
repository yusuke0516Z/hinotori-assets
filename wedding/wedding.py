#!/usr/bin/env python3
"""結婚式準備管理CLI - 辰巳裕亮 & 陳瑞芳"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).parent


# ─────────────────────────────────────────────
# データ読み書き
# ─────────────────────────────────────────────

def load_yaml(filename):
    with open(BASE_DIR / filename, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(filename, data):
    with open(BASE_DIR / filename, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_config():
    return load_yaml("config.yaml")


def load_tasks():
    return load_yaml("tasks.yaml")


# ─────────────────────────────────────────────
# タイムライン計算
# ─────────────────────────────────────────────

WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]


def get_wedding_date(config):
    return date.fromisoformat(config["wedding"]["date"])


def days_until_wedding(config):
    return (get_wedding_date(config) - date.today()).days


def format_countdown(days):
    if days < 0:
        return f"挙式から {abs(days)}日 経過"
    months = days // 30
    remaining_days = days % 30
    if months > 0:
        return f"残り {days}日（約{months}ヶ月{remaining_days}日）"
    return f"残り {days}日"


def is_venue_open(target_date):
    """会場が営業しているか判定（月=0, 火=1 は休館）"""
    return target_date.weekday() not in (0, 1)


def next_contact_day():
    """次に会場へ連絡可能な日を返す"""
    d = date.today()
    for _ in range(7):
        if is_venue_open(d):
            return d
        d += timedelta(days=1)
    return d


def current_phase(tasks_data):
    """現在日付に基づいてフェーズを判定"""
    today = date.today()
    for phase in tasks_data["phases"]:
        # target_periodの終了部分から判定
        period = phase["target_period"]
        if period.startswith("〜"):
            # "〜2026-04" -> 2026-04-30
            end_str = period.replace("〜", "")
            end_date = date.fromisoformat(end_str + "-28")
        elif "〜" in period:
            # "2026-05〜2026-07" -> 2026-07-31
            end_str = period.split("〜")[1]
            end_date = date.fromisoformat(end_str + "-28")
        else:
            # "2027-01-31" -> exact date
            end_date = date.fromisoformat(period)

        if today <= end_date:
            return phase
    return tasks_data["phases"][-1]


def all_tasks(tasks_data):
    """全フェーズの全タスクをフラットに返す"""
    return [t for p in tasks_data["phases"] for t in p["tasks"]]


# ─────────────────────────────────────────────
# コマンド: status
# ─────────────────────────────────────────────

def cmd_status(_args):
    config = load_config()
    tasks_data = load_tasks()
    days = days_until_wedding(config)
    phase = current_phase(tasks_data)
    tasks = all_tasks(tasks_data)

    done = sum(1 for t in tasks if t["status"] == "done")
    in_prog = sum(1 for t in tasks if t["status"] == "in_progress")
    not_started = sum(1 for t in tasks if t["status"] == "not_started")
    overdue = sum(
        1 for t in tasks
        if t["status"] not in ("done", "skipped")
        and t["due_date"]
        and date.fromisoformat(t["due_date"]) < date.today()
    )
    total = len(tasks)

    w = config["wedding"]
    couple = config["couple"]
    print("=" * 45)
    print(f"  {couple['groom']['name']} & {couple['bride']['name']}")
    print(f"  挙式日: {w['date']}（{w['day_of_week']}）")
    print(f"  挙式 {w['ceremony_time']} / 披露宴 {w['reception_time']}")
    print(f"  {format_countdown(days)}")
    print(f"  会場: {config['venue']['name']}")
    print("=" * 45)
    print()
    pct = done * 100 // total if total else 0
    print(f"  進捗: {done}/{total} 完了 ({pct}%)")
    print(f"    完了: {done}  進行中: {in_prog}  未着手: {not_started}")
    if overdue:
        print(f"    \033[31m期限超過: {overdue}\033[0m")
    print()
    print(f"  現在のフェーズ: {phase['name']}")


# ─────────────────────────────────────────────
# コマンド: tasks
# ─────────────────────────────────────────────

STATUS_MARKS = {
    "done": "\033[32m[x]\033[0m",
    "in_progress": "\033[33m[>]\033[0m",
    "not_started": "[ ]",
    "skipped": "\033[90m[-]\033[0m",
}

PRIORITY_MARKS = {"high": " \033[31m!!!\033[0m", "medium": " \033[33m!!\033[0m", "low": ""}


def cmd_tasks(args):
    tasks_data = load_tasks()
    today = date.today()

    for phase in tasks_data["phases"]:
        if args.phase and phase["id"] != args.phase:
            continue

        tasks = phase["tasks"]
        if args.status:
            tasks = [t for t in tasks if t["status"] == args.status]
        if args.overdue:
            tasks = [
                t for t in tasks
                if t["status"] not in ("done", "skipped")
                and t["due_date"]
                and date.fromisoformat(t["due_date"]) < today
            ]

        if not tasks:
            continue

        print(f"\n--- {phase['name']} ---")
        for t in tasks:
            sm = STATUS_MARKS.get(t["status"], "[ ]")
            pm = PRIORITY_MARKS.get(t["priority"], "")
            overdue_mark = ""
            if (t["status"] not in ("done", "skipped")
                    and t["due_date"]
                    and date.fromisoformat(t["due_date"]) < today):
                days_over = (today - date.fromisoformat(t["due_date"])).days
                overdue_mark = f" \033[31m({days_over}日超過)\033[0m"

            print(f"  {sm} {t['id']}: {t['title']} [{t['due_date']}]{pm}{overdue_mark}")
            if t.get("notes"):
                print(f"       {t['notes']}")


# ─────────────────────────────────────────────
# コマンド: update
# ─────────────────────────────────────────────

VALID_STATUSES = ("not_started", "in_progress", "done", "skipped")


def cmd_update(args):
    tasks_data = load_tasks()
    if args.status not in VALID_STATUSES:
        print(f"エラー: ステータスは {', '.join(VALID_STATUSES)} のいずれかを指定してください")
        sys.exit(1)

    for phase in tasks_data["phases"]:
        for task in phase["tasks"]:
            if task["id"] == args.id:
                task["status"] = args.status
                if args.status == "done":
                    task["completed_date"] = date.today().isoformat()
                save_yaml("tasks.yaml", tasks_data)
                print(f"更新: {task['title']} -> {args.status}")
                return

    print(f"エラー: タスクID '{args.id}' が見つかりません")
    sys.exit(1)


# ─────────────────────────────────────────────
# コマンド: remind
# ─────────────────────────────────────────────

def cmd_remind(args):
    tasks_data = load_tasks()
    today = date.today()
    horizon = today + timedelta(days=args.days)

    overdue = []
    upcoming = []

    for t in all_tasks(tasks_data):
        if t["status"] in ("done", "skipped") or not t["due_date"]:
            continue
        due = date.fromisoformat(t["due_date"])
        if due < today:
            overdue.append(t)
        elif due <= horizon:
            upcoming.append(t)

    if overdue:
        print(f"\033[31m--- 期限超過タスク ({len(overdue)}件) ---\033[0m")
        for t in overdue:
            days_over = (today - date.fromisoformat(t["due_date"])).days
            print(f"  {t['id']}: {t['title']} [{t['due_date']}] ({days_over}日超過)")
        print()

    if upcoming:
        print(f"\033[33m--- {args.days}日以内のタスク ({len(upcoming)}件) ---\033[0m")
        for t in sorted(upcoming, key=lambda x: x["due_date"]):
            days_left = (date.fromisoformat(t["due_date"]) - today).days
            print(f"  {t['id']}: {t['title']} [{t['due_date']}] (残り{days_left}日)")
        print()

    if not overdue and not upcoming:
        print(f"直近{args.days}日以内に期限のタスクはありません")


# ─────────────────────────────────────────────
# コマンド: contact
# ─────────────────────────────────────────────

def cmd_contact(_args):
    config = load_config()
    venue = config["venue"]
    ncd = next_contact_day()

    print("=" * 40)
    print(f"  会場: {venue['name']}")
    print("=" * 40)
    print(f"  TEL:  {venue['phone']}")
    print(f"  Mail: {venue['email']}")
    print(f"  件名: {venue['email_subject']}")
    print()
    print(f"  営業時間:")
    print(f"    平日:   {venue['hours']['weekday']}")
    print(f"    土日祝: {venue['hours']['weekend']}")
    print(f"  休館日: {', '.join(venue['closed'])}曜日（祝日除く）")
    print()
    print(f"  次の連絡可能日: {ncd.isoformat()}（{WEEKDAYS_JP[ncd.weekday()]}）")
    if ncd == date.today():
        print("    -> 本日連絡可能です")
    print()
    print(f"  {venue['note']}")


# ─────────────────────────────────────────────
# コマンド: log
# ─────────────────────────────────────────────

def cmd_log(args):
    today = date.today()
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{today.strftime('%Y-%m')}.md"

    date_str = f"{today.isoformat()}（{WEEKDAYS_JP[today.weekday()]}）"

    entry = f"\n## {date_str}\n"
    entry += f"### 実施内容\n- {args.message}\n"
    if args.notes:
        entry += f"\n### メモ\n- {args.notes}\n"
    entry += "\n---\n"

    if not log_file.exists():
        month_str = f"{today.year}年{today.month}月"
        header = f"# {month_str} 結婚準備ログ\n"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(header)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)

    print(f"ログを記録しました: {log_file.name}")
    print(f"  {date_str}: {args.message}")


# ─────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="結婚式準備管理CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="残日数・進捗サマリー表示")

    p_tasks = sub.add_parser("tasks", help="タスク一覧表示")
    p_tasks.add_argument("--phase", help="フェーズIDでフィルター (例: phase_01)")
    p_tasks.add_argument("--status", help="ステータスでフィルター")
    p_tasks.add_argument("--overdue", action="store_true", help="期限超過タスクのみ")

    p_update = sub.add_parser("update", help="タスクステータス更新")
    p_update.add_argument("--id", required=True, help="タスクID (例: t001)")
    p_update.add_argument("--status", required=True, help="新ステータス")

    p_remind = sub.add_parser("remind", help="期限近いタスク表示")
    p_remind.add_argument("--days", type=int, default=14, help="表示する日数範囲 (デフォルト: 14)")

    sub.add_parser("contact", help="会場連絡先表示")

    p_log = sub.add_parser("log", help="ログ追記")
    p_log.add_argument("--message", "-m", required=True, help="実施内容")
    p_log.add_argument("--notes", "-n", help="メモ")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "status": cmd_status,
        "tasks": cmd_tasks,
        "update": cmd_update,
        "remind": cmd_remind,
        "contact": cmd_contact,
        "log": cmd_log,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
