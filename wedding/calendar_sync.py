#!/usr/bin/env python3
"""Google Calendar連携スクリプト

セットアップ手順:
1. Google Cloud Console (https://console.cloud.google.com/) でプロジェクトを作成
2. Google Calendar API を有効化
3. OAuth 2.0 クライアントIDを作成（デスクトップアプリ）
4. 認証情報JSONをダウンロードし、このファイルと同じディレクトリに credentials.json として配置
5. 必要パッケージをインストール:
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
6. 初回実行時にブラウザが開き、Googleアカウントの認証を行う
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).parent
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_SUMMARY = "結婚式準備"
TOKEN_FILE = BASE_DIR / "token.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"


def load_tasks():
    with open(BASE_DIR / "tasks.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_calendar_service():
    """Google Calendar APIサービスを取得"""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("エラー: 必要なパッケージがインストールされていません")
        print("以下を実行してください:")
        print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        sys.exit(1)

    if not CREDENTIALS_FILE.exists():
        print(f"エラー: {CREDENTIALS_FILE} が見つかりません")
        print("Google Cloud ConsoleからOAuth2認証情報をダウンロードしてください")
        sys.exit(1)

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def find_or_create_calendar(service):
    """結婚式準備用カレンダーを取得または作成"""
    calendars = service.calendarList().list().execute()
    for cal in calendars.get("items", []):
        if cal["summary"] == CALENDAR_SUMMARY:
            return cal["id"]

    new_cal = service.calendars().insert(body={"summary": CALENDAR_SUMMARY}).execute()
    print(f"カレンダー '{CALENDAR_SUMMARY}' を作成しました")
    return new_cal["id"]


def cmd_sync(args):
    """全タスクの期限をカレンダーに同期"""
    service = get_calendar_service()
    calendar_id = find_or_create_calendar(service)
    tasks_data = load_tasks()

    synced = 0
    for phase in tasks_data["phases"]:
        for task in phase["tasks"]:
            if task["status"] in ("done", "skipped"):
                continue
            if not task["due_date"]:
                continue

            event = {
                "summary": f"[{task['priority'].upper()}] {task['title']}",
                "description": f"タスクID: {task['id']}\nフェーズ: {phase['name']}\n{task.get('notes', '')}",
                "start": {"date": task["due_date"]},
                "end": {"date": task["due_date"]},
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 1440},  # 1日前
                        {"method": "popup", "minutes": 10080},  # 1週間前
                    ],
                },
            }

            service.events().insert(calendarId=calendar_id, body=event).execute()
            synced += 1
            print(f"  同期: {task['title']} [{task['due_date']}]")

    print(f"\n{synced}件のタスクをカレンダーに同期しました")


def cmd_add(args):
    """個別タスクをカレンダーに追加"""
    service = get_calendar_service()
    calendar_id = find_or_create_calendar(service)
    tasks_data = load_tasks()

    for phase in tasks_data["phases"]:
        for task in phase["tasks"]:
            if task["id"] == args.id:
                event = {
                    "summary": f"[{task['priority'].upper()}] {task['title']}",
                    "description": f"タスクID: {task['id']}\nフェーズ: {phase['name']}\n{task.get('notes', '')}",
                    "start": {"date": task["due_date"]},
                    "end": {"date": task["due_date"]},
                }
                service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f"カレンダーに追加: {task['title']} [{task['due_date']}]")
                return

    print(f"エラー: タスクID '{args.id}' が見つかりません")
    sys.exit(1)


def cmd_clear(args):
    """同期済みイベントをクリア"""
    service = get_calendar_service()
    calendar_id = find_or_create_calendar(service)

    events = service.events().list(calendarId=calendar_id, maxResults=250).execute()
    items = events.get("items", [])

    if not items:
        print("クリアするイベントはありません")
        return

    for event in items:
        service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()

    print(f"{len(items)}件のイベントをクリアしました")


def main():
    parser = argparse.ArgumentParser(description="Google Calendar連携")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("sync", help="全タスクの期限をカレンダーに同期")

    p_add = sub.add_parser("add", help="個別タスクをカレンダーに追加")
    p_add.add_argument("--id", required=True, help="タスクID (例: t001)")

    sub.add_parser("clear", help="同期済みイベントをクリア")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    {"sync": cmd_sync, "add": cmd_add, "clear": cmd_clear}[args.command](args)


if __name__ == "__main__":
    main()
