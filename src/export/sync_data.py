from pathlib import Path

from databse.mongo_db import get_db
from export.parse_xlsx import (
    add_test_client,
    insert_shipments,
    load_shipments_from_excel,
)


def sync_all():
    db = get_db()

    print("📦 Загружаем посылки из Excel...")

    # --- путь к папке с файлами ---
    base_dir = Path(__file__).resolve().parent
    files_dir = base_dir / "files"

    if not files_dir.exists():
        print(f"⚠️ Папка {files_dir} не найдена!")
        return

    # --- ищем все Excel-файлы ---
    excel_files = [f for f in files_dir.glob("*.xlsx")]
    if not excel_files:
        print(f"⚠️ Excel-файлы не найдены в {files_dir}")
        return

    for file_path in excel_files:
        print(f"📂 Импортируем файл: {file_path.name}")
        shipments = load_shipments_from_excel(str(file_path))
        insert_shipments(shipments, db)

    # --- добавляем тестового клиента ---
    add_test_client(db)

    print("✅ Синхронизация завершена!")


if __name__ == "__main__":
    # sync_all()
    ...
