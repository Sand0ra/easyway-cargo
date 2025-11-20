from python_calamine import CalamineWorkbook


def load_shipments_from_excel(xlsx_path: str):
    workbook = CalamineWorkbook.from_path(xlsx_path)
    sheet = workbook.get_sheet_by_name("Sheet1").to_python()
    rows = sheet[2:]
    shipments = []

    for row in rows:
        if len(row) < 6:
            continue
        shipments.append({
            "date_sent": row[0],
            "client_code": row[1],
            "track_number": row[2],
            "paid_in_gz": row[3],
            "weight": row[4],
            "bag_number": row[5],
            "received_date": row[6] if len(row) > 6 else "",
            "status": "получена" if (len(row) > 6 and row[6]) else "в пути"
        })
    return shipments


def insert_shipments(shipments, db):
    """Сохраняем посылки в базу"""
    collection = db.shipments
    for s in shipments:
        collection.update_one(
            {"track_number": s["track_number"]},
            {"$set": s},
            upsert=True
        )
    print(f"✅ Загружено {len(shipments)} посылок.")


def add_test_client(db):
    """Добавляем тестового клиента"""
    client_data = {
        "code": "F-1000",
        "name": "Тестовый Клиент",
        "phone": "996501592328",
        "address": "г. Бишкек, ул. Примерная 10",
        "pvz": "Центральный ПВЗ"
    }
    db.clients.update_one({"phone": client_data["phone"]}, {"$set": client_data}, upsert=True)
    print("✅ Добавлен тестовый клиент:", client_data["phone"])

