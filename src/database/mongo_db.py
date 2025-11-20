from pymongo import MongoClient


def get_db():
    mongo_url = "mongodb://mongo:27017/cargo_bot"
    client = MongoClient(mongo_url)
    return client["cargo_bot"]


mongo_db = get_db()


def get_client_by_phone(phone: str):
    phone = phone.replace("+", "").strip()

    variants = [
        phone[1:],
        phone,  # как есть (+996501592328)
        phone[3:],  # 501592328 (убрали 996)
        "0" + phone[3:],  # 0501592328
    ]
    print(variants)
    variants = list(set(variants))  # убрать дубли

    return mongo_db.clients.find_one({"phone": {"$in": variants}})


def get_active_shipments(client_code):
    return list(
        mongo_db.shipments.find(
            {"client_code": client_code, "status": {"$ne": "получена"}}
        )
    )


def save_client(client_data: dict):
    mongo_db.clients.update_one(
        {"phone": client_data["phone"]},  # критерий уникальности
        {"$setOnInsert": client_data},  # данные вставятся только если записи нет
        upsert=True,
    )


def save_shipment(shipment_data: dict):
    mongo_db.shipments.update_one(
        {"tracking_number": shipment_data["tracking_number"]},  # критерий уникальности
        {"$setOnInsert": shipment_data},  # данные вставятся только если записи нет
        upsert=True,
    )
