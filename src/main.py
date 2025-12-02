import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from database.mongo_db import (
    get_active_shipments,
    get_client_by_phone,
    get_next_client_code,
    save_client,
    save_shipment,
)
from export.google_sheets import periodic_sync
from export.write_to_sheets import add_client_to_sheet, add_shipment_to_sheet

BOT_TOKEN = "7996530552:AAFWtFFSQbhZGQ5AcIaC1PhQEJaclsO90qM"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_sessions = {}
pending_registration = {}

BASE_DIR = Path(__file__).resolve().parent
FILES_DIR = BASE_DIR / "export" / "files"

def main_menu():
    """Главное меню с красивыми эмодзи"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Ваши данные")],
            [KeyboardButton(text="🏢 Адрес склада в Китае")],
            [KeyboardButton(text="📦 Актуальные посылки")],
            [KeyboardButton(text="🎥 Видео инструкция")],
            [KeyboardButton(text="❓ FAQ")],
            [KeyboardButton(text="📞 Связаться с нами")],
            [KeyboardButton(text="➕ Добавить трек")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел 👇"
    )
    return kb


share_phone_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start с приветственным сообщением"""
    welcome_text = (
        "🎉 Добро пожаловать в EasyWay Cargo!\n\n"
        "Для доступа к персональным данным и отслеживанию посылок "
        "нам нужен ваш номер телефона.\n\n"
        "📲 Нажмите кнопку ниже, чтобы поделиться номером:"
    )

    await message.answer(welcome_text, reply_markup=share_phone_kb)


@dp.message(F.contact)
async def auth_user(message: Message):
    """Аутентификация пользователя по номеру телефона"""
    phone = message.contact.phone_number
    print("🔐 Получен номер:", phone)

    client = get_client_by_phone(phone)
    print("👤 Найден клиент:", client)

    user_id = message.from_user.id
    chat_id = message.chat.id

    if client is None:
        pending_registration[user_id] = {
            "phone": phone,
            "step": "name"
        }
        error_text = (
            "❌ Ваш номер не найден в базе\n\n"
            "Чтобы зарегистрироваться, отправьте ваше *ФИО*."
        )
        await message.answer(error_text)
        return

    if client.get("chat_id") != chat_id:
        client["chat_id"] = chat_id
        save_client(client)

    user_sessions[user_id] = client

    welcome_back_text = (
        f"👤 <b>ВАШИ ДАННЫЕ</b>\n"
        "─────────────\n"
        f"🎫 <b>Персональный код:</b>\n"
        f"   <code>{client['client_code']}</code>\n\n"
        f"📛 <b>ФИО:</b>\n"
        f"   {client.get('name', 'Не указано')}\n\n"
        f"📞 <b>Телефон:</b>\n"
        f"   {client.get('phone', 'Не указан')}\n\n"
        f"💡 Для изменения данных обратитесь в поддержку"
    )

    await message.answer(welcome_back_text, reply_markup=main_menu(), parse_mode="HTML")


@dp.message(F.text == "👤 Ваши данные")
async def my_data(message: Message):
    """Отображение данных пользователя"""
    client = user_sessions.get(message.from_user.id)
    if not client:
        await message.answer("🔒 Сначала авторизуйтесь через /start")
        return

    client_data = get_client_by_phone(client["phone"])
    if not client_data:
        await message.answer("❌ Ваши данные не найдены в базе")
        return

    profile_text = (
        f"👤 <b>ВАШИ ДАННЫЕ</b>\n"
        "─────────────\n"
        f"🎫 <b>Персональный код:</b>\n"
        f"   <code>{client_data['client_code']}</code>\n\n"
        f"📛 <b>ФИО:</b>\n"
        f"   {client_data.get('name', 'Не указано')}\n\n"
        f"📞 <b>Телефон:</b>\n"
        f"   {client_data.get('phone', 'Не указан')}\n\n"
        f"💡 Для изменения данных обратитесь в поддержку"
    )

    await message.answer(profile_text, parse_mode="HTML")


@dp.message(F.text == "🏢 Адрес склада в Китае")
async def warehouse(message: Message):
    client = user_sessions.get(message.from_user.id)
    if not client:
        await message.answer("🔒 Сначала авторизуйтесь через /start")
        return

    help_text = (
        "Скопируйте текст ниже. Это адрес склада в Китае"
    )

    warehouse_text = (
        f"收货人: {client['client_code']}\n"
        "广东省广州市越秀区荔德路318号\n"
        "汇富国际A27栋103号 1899库房\n"
        f"比什凯克 {client['phone']} 唛头 F-код\n"
        "电话: 13711589799\n\n"
    )

    important_text = (
        "<b>Важно:</b>\n"
        "Обязательно отправьте скриншот заполненного адреса менеджеру.\n"
        "Только после подтверждения правильности заполнения мы несём ответственность за груз.\n\n"
        "Менеджер: 0998 001688"
    )

    photo_path = FILES_DIR / "5262799002216893718.jpg"

    photo = FSInputFile(photo_path)

    await message.answer(help_text, parse_mode="HTML")
    await message.answer(warehouse_text, parse_mode="HTML")
    await message.answer_photo(photo=photo, caption=important_text, parse_mode="HTML")


@dp.message(F.text == "📦 Актуальные посылки")
async def current_tracks(message: Message):
    """Отображение активных посылок"""
    client = user_sessions.get(message.from_user.id)

    if not client:
        await message.answer("🔒 Сначала авторизуйтесь через /start")
        return

    fcode = client["client_code"]
    shipments = get_active_shipments(fcode)

    if not shipments:
        empty_text = (
            "📦 <b>АКТУАЛЬНЫЕ ПОСЫЛКИ</b>\n"
            "─────────────\n\n"
            "😔 У вас пока нет активных посылок\n\n"
            "💡 Добавьте трек-номер через меню '➕ Добавить трек'"
        )
        await message.answer(empty_text, parse_mode="HTML")
        return

    header_text = (
        "📦 <b>ВАШИ АКТИВНЫЕ ПОСЫЛКИ</b>\n"
        "─────────────\n\n"
    )

    shipment_texts = []
    for i, shipment in enumerate(shipments, 1):
        tracking = shipment.get("tracking_number") or "—"
        sent_date = shipment.get("sent_date") or "Еще не отправлен"
        weight_kg = shipment.get("weight_kg")
        weight_str = f"{weight_kg} кг" if weight_kg else "—"
        bag_number = shipment.get("bag_number") or "—"

        shipment_text = (
            f"<b>Посылка #{i}</b>\n"
            f"📮 <b>Трек:</b> <code>{tracking}</code>\n"
            f"📅 <b>Отправлен:</b> {sent_date}\n"
            f"⚖️ <b>Вес:</b> {weight_str}\n"
            f"🎒 <b>Мешок:</b> {bag_number}\n"
            "─────────────"
        )
        shipment_texts.append(shipment_text)

    # Разбиваем сообщение если посылок много
    full_text = header_text + "\n\n".join(shipment_texts)

    if len(full_text) > 4096:
        # Если сообщение слишком длинное, разбиваем на части
        parts = []
        current_part = header_text
        for shipment_text in shipment_texts:
            if len(current_part + "\n\n" + shipment_text) > 4096:
                parts.append(current_part)
                current_part = shipment_text
            else:
                current_part += "\n\n" + shipment_text
        parts.append(current_part)

        for part in parts:
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(full_text, parse_mode="HTML")


@dp.message(F.text == "🎥 Видео инструкция")
async def video_instruction(message: Message):
    """Отправка видео инструкций"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Taobao",
                    url="https://youtube.com/shorts/FjjB6uNWh2Y?feature=shareё",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏪 1688",
                    url="https://youtube.com/shorts/jcecBGNvkj8?feature=share",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👟 Poizon",
                    url="https://youtube.com/shorts/y40P6sRT5tc?feature=share",
                )
            ],
        ]
    )

    video_text = (
        "🎥 <b>ВИДЕО ИНСТРУКЦИИ</b>\n"
        "─────────────\n\n"
        "📹 Выберите платформу для просмотра инструкции по заказу:\n\n"
        "💡 В видео подробно показано:\n"
        "• Как оформить заказ\n"
        "• Как указать адрес склада\n"
        "• Что делать после заказа"
    )

    await message.answer(video_text, reply_markup=kb, parse_mode="HTML")


@dp.message(F.text == "❓ FAQ")
async def faq(message: Message):
    """Часто задаваемые вопросы"""
    faq_text = (
        "❓ <b>ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ</b>\n"
        "─────────────\n\n"
        "<b>🚫 Запрещённые товары:</b>\n"
        "• Взрывоопасные вещества\n"
        "• Ядовитые и химические вещества\n"
        "• Растения и семена\n"
        "• Оружие и боеприпасы\n"
        "• Лекарства без рецепта\n"
        "• Алкоголь и табачные изделия\n\n"
        "<b>📏 Минимальный вес:</b>\n"
        "• 100 грамм\n\n"
        "<b>⏱️ Сроки доставки:</b>\n"
        "• 8–12 дней\n\n"
    )

    await message.answer(faq_text, parse_mode="HTML")


@dp.message(F.text == "📞 Связаться с нами")
async def contact(message: Message):
    """Контактная информация"""
    contact_text = (
        "📞 <b>СВЯЗАТЬСЯ С НАМИ</b>\n"
        "─────────────\n\n"
        "💬 Мы всегда рады помочь вам!\n\n"
        "<b>📱 WhatsApp:</b>\n"
        "📞 0998 001688\n\n"
        "<b>📸 Instagram:</b>\n"
        "@easyway_cargo_kg\n\n"
        "<b>📢 Telegram канал:</b>\n"
        "Скоро будет...\n\n"
    )

    await message.answer(contact_text, parse_mode="HTML")


@dp.message(F.text == "➕ Добавить трек")
async def ask_track(message: Message):
    """Запрос трек-номера"""
    client = user_sessions.get(message.from_user.id)
    if not client:
        await message.answer("🔒 Сначала авторизуйтесь через /start")
        return

    track_text = (
        "➕ <b>ДОБАВЛЕНИЕ ТРЕК-НОМЕРА</b>\n"
        "─────────────\n\n"
        "📮 Отправьте трек-номер одной посылки\n\n"
        "💡 Примеры трек-номеров:\n"
        "• RB123456789CN\n"
        "• UH0012345678\n"
        "• 123456789012\n\n"
        "⚠️ Отправляйте только один трек-номер за раз"
    )

    await message.answer(track_text, parse_mode="HTML")


@dp.message(F.text.regexp(r"^[A-Za-z0-9]{8,20}$"))
async def add_track(message: Message):
    """Добавление трек-номера"""
    client = user_sessions.get(message.from_user.id)

    if not client:
        await message.answer("🔒 Сначала авторизуйтесь через /start")
        return

    track = message.text.strip().upper()

    # Проверяем авторизацию через сессию
    if not client.get("phone"):
        await message.answer("❌ Ошибка авторизации. Пожалуйста, перезапустите бота через /start")
        return

    data = {
        "tracking_number": track,
        "client_code": client["client_code"]
    }

    try:

        success_text = (
            f"✅ <b>ТРЕК-НОМЕР УСПЕШНО ДОБАВЛЕН!</b>\n"
            "─────────────\n\n"
            f"📮 <b>Трек:</b> <code>{track}</code>\n"
            f"👤 <b>Клиент:</b> {client.get('name', 'Не указано')}\n"
            f"🎫 <b>Код:</b> <code>{client['client_code']}</code>\n\n"
            "💡 Посылка появится в разделе '📦 Актуальные посылки' после обработки"
        )
        await message.answer(success_text, parse_mode="HTML")
        save_shipment(data)
        add_shipment_to_sheet(data)
    except Exception as e:
        error_text = (
            f"❌ <b>ОШИБКА ДОБАВЛЕНИЯ</b>\n"
            "─────────────\n\n"
            f"Не удалось добавить трек-номер <code>{track}</code>\n\n"
            "⚠️ Пожалуйста, попробуйте позже или обратитесь в поддержку"
        )
        await message.answer(error_text, parse_mode="HTML")
        print(f"Ошибка при добавлении трека: {e}")

@dp.message(lambda m: m.from_user.id in pending_registration)
async def registration_handler(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in pending_registration:
        return

    name = message.text.strip()
    phone = pending_registration[user_id]["phone"]

    client_code, code_number = get_next_client_code()

    new_client = {
        "name": name,
        "phone": phone,
        "client_code": client_code,
        "code_number": code_number,
        "chat_id": chat_id,
    }

    save_client(new_client)

    user_sessions[user_id] = new_client

    del pending_registration[user_id]

    await message.answer(
        f"🎉 <b>Регистрация завершена!</b>\n\n"
        f"📛 <b>ФИО:</b> {name}\n"
        f"🎫 <b>Код:</b> <code>{client_code}</code>\n"
        f"📞 <b>Телефон:</b> {phone}\n\n"
        f"Теперь вы можете пользоваться ботом.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    add_client_to_sheet(client_code, name, phone)


@dp.message()
async def unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    help_text = (
        "🤖 <b>КОМАНДЫ БОТА</b>\n"
        "─────────────\n\n"
        "Используйте кнопки меню ниже или команды:\n\n"
        "🔹 /start - Начать работу\n"
        "🔹 /help - Помощь\n\n"
        "💡 Если что-то не работает - обратитесь в поддержку через раздел '📞 Связаться с нами'"
    )

    await message.answer(help_text, reply_markup=main_menu(), parse_mode="HTML")


async def main():
    """Основная функция запуска бота"""
    print("🚀 Бот EasyWay Cargo запущен!")
    print("📞 Ожидание сообщений...")

    try:
        sync_task = asyncio.create_task(periodic_sync(bot))

        await dp.start_polling(bot)

        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass

    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
