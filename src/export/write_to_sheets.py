from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

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

def get_google_sheet(key: str):
    gc = gspread.authorize(creds)
    return gc.open_by_key(key).sheet1


def add_client_to_sheet(client_code: str, name: str, phone: str):
    sheet = get_google_sheet(SPREADSHEETS["clients"])
    sheet.append_row([client_code, name, phone])


def add_shipment_to_sheet(data: dict):
    sheet = get_google_sheet(SPREADSHEETS["shipments"])
    sheet.append_row([
        "",                 # Дата отправки (пусто)
        data["client_code"],
        data["tracking_number"],
        "",                 # Оплачено в gz
        "",                 # КГ
        "",                 # Номер мешка
        "",                 # Дата доставки
    ])
