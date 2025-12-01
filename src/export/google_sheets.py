import asyncio
import sys
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

from database.mongo_db import mongo_db, save_client, save_shipment
from notify import notify_client_about_sent

sys.path.append(str(Path(__file__).resolve().parent.parent))


BASE_DIR = Path(__file__).resolve().parent
FILES_DIR = BASE_DIR / "files"
CREDENTIALS_FILE = FILES_DIR / "google_credentials.json"

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEETS = {
    "clients": "1q5F5Z_HFhVUSvdtT2xcuHUODUUTP0jz347gxXZa-QIM",
    "shipments": "1fFZvbP_b6g-ol2aMxxeHl41ae4kRQAn1-HHuASOoWZo",
}


creds = Credentials.from_service_account_file(
    CREDENTIALS_FILE,
    scopes=GOOGLE_SCOPES,
)

# ==========================================================

def get_google_sheet(key: str):
    gc = gspread.authorize(creds)
    return gc.open_by_key(key).sheet1


def parse_sheet(key: str) -> List[Dict]:
    try:
        sheet = get_google_sheet(key)
        return sheet.get_all_records()
    except Exception as e:
        print(f"Ошибка при парсинге таблицы ({key}): {e}")
        return []


def normalize_phone(phone: str) -> str:
    phone = phone.replace("+", "").strip()
    if phone.startswith("0"):
        phone = phone[1:]
    return phone


def to_float(v) -> Optional[float]:
    try:
        return float(str(v).replace(",", "."))
    except:
        return None


def to_str(v) -> str:
    return str(v).strip() if v is not None else ""


def parse_code(client_code: str) -> int:
    if not client_code:
        return 0

    digits = "".join(ch for ch in client_code if ch.isdigit())

    return int(digits) if digits else 0



def process_client_row(row: dict) -> dict:
    code = to_str(row.get("Персональный код"))
    return {
        "client_code": code,
        "code_number": parse_code(code),
        "name": to_str(row.get("ФИО")),
        "phone": normalize_phone(to_str(row.get("номер телефона"))),
    }


def process_shipment_row(row: dict) -> dict:
    return {
        "sent_date": to_str(row.get("Дата отправки")),
        "client_code": to_str(row.get("Код груза")),
        "tracking_number": to_str(row.get("Трекинг номер")),
        "paid_gz": to_float(row.get("Оплачено в gz")),
        "weight_kg": to_float(row.get("КГ")),
        "bag_number": to_str(row.get("Номер мешка")),
        "delivery_date": to_str(row.get("Дата доставки")),
    }


def sync_clients():
    rows = parse_sheet(SPREADSHEETS["clients"])
    for row in rows:
        data = process_client_row(row)
        save_client(data)
    print(f"Синхронизировано клиентов: {len(rows)}")


async def sync_shipments(bot):
    rows = parse_sheet(SPREADSHEETS["shipments"])

    for row in rows:
        data = process_shipment_row(row)

        tracking = data["tracking_number"]
        if not tracking:
            continue

        existing = mongo_db.shipments.find_one({"tracking_number": tracking})

        save_shipment(data)

        if data["sent_date"] and (not existing or not existing.get("sent_date")):
            await notify_client_about_sent(bot, data)

    print(f"Синхронизировано отправлений: {len(rows)}")


async def run_sync(fn, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args))


async def periodic_sync(bot):
    while True:
        print("🔄 Синхронизация Google Sheet → MongoDB…")

        try:
            await run_sync(sync_clients)
            await sync_shipments(bot)  # ← Теперь это async функция

            print("✅ Синхронизация завершена!")
        except Exception as e:
            print("❌ Ошибка синхронизации:", e)

        await asyncio.sleep(60 * 60)

