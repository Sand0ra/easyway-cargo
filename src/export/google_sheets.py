from pathlib import Path
from typing import Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials
from pymongo import MongoClient


# ==========================================================
# DATABASE
# ==========================================================

def get_db():
    mongo_url = "mongodb://mongo:27017/cargo_bot"
    client = MongoClient(mongo_url)
    return client["cargo_bot"]


mongo_db = get_db()


# ==========================================================
# SAVE FUNCTIONS (UPSERT)
# ==========================================================

def save_client(client_data: dict):
    mongo_db.clients.update_one(
        {"client_code": client_data["client_code"]},
        {"$set": client_data},
        upsert=True,
    )


def save_shipment(shipment_data: dict):
    mongo_db.shipments.update_one(
        {"tracking_number": shipment_data["tracking_number"]},
        {"$set": shipment_data},
        upsert=True,
    )


# ==========================================================
# CONFIG
# ==========================================================

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
# HELPERS
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


# ==========================================================
# FIELD NORMALIZERS
# ==========================================================

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


# ==========================================================
# DATA PROCESSORS
# ==========================================================

def process_client_row(row: dict) -> dict:
    """
    Приводим данные клиента к стандартной структуре.
    """
    return {
        "client_code": to_str(row.get("Персональный код")),
        "name": to_str(row.get("ФИО")),
        "phone": normalize_phone(to_str(row.get("номер телефона"))),
    }


def process_shipment_row(row: dict) -> dict:
    """
    Приводим данные отправления к нашей унифицированной структуре.
    """
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


def sync_shipments():
    rows = parse_sheet(SPREADSHEETS["shipments"])
    for row in rows:
        data = process_shipment_row(row)
        save_shipment(data)
    print(f"Синхронизировано отправлений: {len(rows)}")


if __name__ == "__main__":
    sync_clients()
    sync_shipments()
