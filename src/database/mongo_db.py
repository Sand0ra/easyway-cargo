from pymongo import MongoClient


def get_db():
    mongo_url = "mongodb://mongo:27017/cargo_bot"
    client = MongoClient(mongo_url)
    return client["cargo_bot"]


mongo_db = get_db()


def get_client_by_phone(phone: str):
    variants = [
        phone[1:], # 996501592328
        phone,  # +996501592328
        phone[4:],  # 501592328
        "0" + phone[4:],  # 0501592328
    ]
    print(variants)
    variants = list(set(variants))

    return mongo_db.clients.find_one({"phone": {"$in": variants}})


def get_active_shipments(client_code):
    return list(
        mongo_db.shipments.find(
            {"client_code": client_code, "status": {"$ne": "получена"}}
        )
    )


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


def get_next_client_code():
    last = mongo_db.clients.find_one(
        {"code_number": {"$exists": True}},
        sort=[("code_number", -1)]
    )

    if not last:
        next_num = 1
    else:
        next_num = int(last["code_number"]) + 1

    return f"f-{next_num:04d}", next_num
