from database.mongo_db import mongo_db


async def notify_client_about_sent(bot, shipment: dict):
    client = mongo_db.clients.find_one({"client_code": shipment["client_code"]})
    if not client or "chat_id" not in client:
        print("Клиент не найден или нет chat_id")
        return

    text = (
        f"📦 Ваш груз отправлен!\n\n"
        f"🔢 Трекинг: <code>{shipment['tracking_number']}</code>\n"
        f"📅 Дата отправки: {shipment['sent_date']}"
    )

    try:
        await bot.send_message(client["chat_id"], text, parse_mode="HTML")
        print(f"Отправлено уведомление клиенту {client['client_code']}")
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")
