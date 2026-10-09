import os
import sqlite3
from datetime import datetime

from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = "applications.db"

FIELDS = [
    ("name", "Как вас зовут?"),
    ("phone", "Отправьте номер телефона кнопкой ниже или напишите его вручную."),
    ("brand", "Введите марку автомобиля.\nНапример: BMW"),
    ("model", "Введите модель.\nНапример: 320i"),
    ("year", "Введите год выпуска.\nНапример: 2020"),
    ("mileage", "Введите пробег в километрах.\nНапример: 78000"),
    ("city", "Введите город."),
    ("condition", "Опишите состояние автомобиля.\nНапример: хорошее, есть небольшие царапины."),
    ("accident", "Был ли автомобиль в ДТП?"),
    ("price", "Какую сумму хотите получить за автомобиль?\nНапример: 2100000"),
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            name TEXT,
            phone TEXT,
            brand TEXT,
            model TEXT,
            year TEXT,
            mileage TEXT,
            city TEXT,
            condition TEXT,
            accident TEXT,
            price TEXT,
            status TEXT DEFAULT 'Новая',
            created_at TEXT
        )
    """)
    conn.commit()
    return conn

def add_application(user_id, username, data):
    conn = db()
    cur = conn.execute("""
        INSERT INTO applications
        (user_id, username, name, phone, brand, model, year, mileage,
         city, condition, accident, price, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, username, data.get("name"), data.get("phone"),
        data.get("brand"), data.get("model"), data.get("year"),
        data.get("mileage"), data.get("city"), data.get("condition"),
        data.get("accident"), data.get("price"),
        datetime.now().strftime("%d.%m.%Y %H:%M")
    ))
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    return app_id

def update_status(app_id, status):
    conn = db()
    conn.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    row = conn.execute(
        "SELECT user_id FROM applications WHERE id=?", (app_id,)
    ).fetchone()
    conn.commit()
    conn.close()
    return row[0] if row else None

def application_text(app_id, data):
    return (
        f"🚗 *НОВАЯ ЗАЯВКА НА ВЫКУП №{app_id}*\n\n"
        f"👤 Имя: {data.get('name', '-')}\n"
        f"📞 Телефон: {data.get('phone', '-')}\n\n"
        f"🚘 Автомобиль: {data.get('brand', '-')} {data.get('model', '-')}\n"
        f"📅 Год: {data.get('year', '-')}\n"
        f"🛣 Пробег: {data.get('mileage', '-')} км\n"
        f"📍 Город: {data.get('city', '-')}\n"
        f"🔧 Состояние: {data.get('condition', '-')}\n"
        f"💥 ДТП: {data.get('accident', '-')}\n"
        f"💰 Желаемая цена: {data.get('price', '-')} ₽\n\n"
        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"📌 Статус: *Новая*"
    )

def admin_keyboard(app_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ В работу", callback_data=f"work:{app_id}"),
            InlineKeyboardButton("❌ Отказ", callback_data=f"reject:{app_id}")
        ],
        [
            InlineKeyboardButton("💰 Предложить цену", callback_data=f"offer:{app_id}")
        ]
    ])

def main_keyboard():
    return ReplyKeyboardMarkup(
        [["🚗 Оставить заявку"]],
        resize_keyboard=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🚗 *Выкуп автомобилей*\n\n"
        "Хотите быстро продать автомобиль? "
        "Оставьте заявку — мы свяжемся с вами и оценим автомобиль.\n\n"
        "Нажмите кнопку ниже, чтобы начать.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def start_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["state"] = "name"
    context.user_data["data"] = {}
    await update.message.reply_text(
        "Начнём оформление заявки.\n\n"
        "Как вас зовут?",
        reply_markup=ReplyKeyboardRemove()
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    state = context.user_data.get("state")

    if text == "🚗 Оставить заявку":
        await start_application(update, context)
        return

    if not state:
        await update.message.reply_text(
            "Нажмите «🚗 Оставить заявку», чтобы начать.",
            reply_markup=main_keyboard()
        )
        return

    data = context.user_data.setdefault("data", {})

    if state == "name":
        data["name"] = text
        context.user_data["state"] = "phone"
        keyboard = ReplyKeyboardMarkup(
            [[
                # Telegram automatically sends the user's contact after tapping.
                # This is only a request button; manual input remains supported.
                __import__("telegram").KeyboardButton(
                    "📞 Отправить мой номер", request_contact=True
                )
            ]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await update.message.reply_text(
            "Укажите номер телефона для связи.",
            reply_markup=keyboard
        )
        return

    if state == "phone":
        data["phone"] = text
        context.user_data["state"] = "brand"
        await update.message.reply_text(
            "Введите марку автомобиля.\nНапример: BMW",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    prompts = {
        "brand": ("brand", "Введите модель.\nНапример: 320i"),
        "model": ("model", "Введите год выпуска.\nНапример: 2020"),
        "year": ("year", "Введите пробег в километрах.\nНапример: 78000"),
        "mileage": ("mileage", "Введите город."),
        "city": ("city", "Опишите состояние автомобиля.\nНапример: хорошее, есть небольшие царапины."),
        "condition": ("condition", "Был ли автомобиль в ДТП?\nНапример: нет / да"),
        "accident": ("accident", "Какую сумму хотите получить за автомобиль?\nНапример: 2100000"),
    }

    if state in prompts:
        key, next_prompt = prompts[state]
        data[key] = text
        next_state = {
            "brand": "model",
            "model": "year",
            "year": "mileage",
            "mileage": "city",
            "city": "condition",
            "condition": "accident",
            "accident": "price",
        }[state]
        context.user_data["state"] = next_state
        await update.message.reply_text(next_prompt)
        return

    if state == "price":
        data["price"] = text
        context.user_data["state"] = "photos"
        await update.message.reply_text(
            "📸 Теперь отправьте фотографии автомобиля.\n\n"
            "Можно отправить несколько фото по одному.\n"
            "Когда закончите, напишите *ГОТОВО*.",
            parse_mode="Markdown"
        )
        return

    if state == "photos":
        if text.upper() == "ГОТОВО":
            await finish_application(update, context)
        else:
            await update.message.reply_text(
                "Отправьте фотографию автомобиля или напишите *ГОТОВО*.",
                parse_mode="Markdown"
            )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if state != "phone":
        return

    contact = update.message.contact
    context.user_data.setdefault("data", {})["phone"] = contact.phone_number
    context.user_data["state"] = "brand"

    await update.message.reply_text(
        "Спасибо! Теперь введите марку автомобиля.\nНапример: BMW",
        reply_markup=ReplyKeyboardRemove()
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "photos":
        await update.message.reply_text(
            "Сначала начните оформление заявки: «🚗 Оставить заявку»."
        )
        return

    photos = context.user_data.setdefault("photos", [])
    photos.append(update.message.photo[-1].file_id)

    await update.message.reply_text(
        f"Фото №{len(photos)} получено. "
        "Отправьте ещё фото или напишите *ГОТОВО*.",
        parse_mode="Markdown"
    )

async def finish_application(update, context):
    data = context.user_data.get("data", {})
    photos = context.user_data.get("photos", [])

    required = ["name", "phone", "brand", "model", "year",
                "mileage", "city", "condition", "accident", "price"]

    if any(not data.get(k) for k in required):
        await update.message.reply_text("Заявка заполнена не полностью. Начните заново.")
        context.user_data.clear()
        return

    app_id = add_application(
        update.effective_user.id,
        update.effective_user.username or "",
        data
    )

    await update.message.reply_text(
        f"✅ *Заявка №{app_id} принята!*\n\n"
        "Спасибо. Мы получили данные автомобиля и свяжемся с вами для дальнейшей оценки.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    if ADMIN_ID:
        await context.bot.send_message(
            ADMIN_ID,
            application_text(app_id, data),
            parse_mode="Markdown",
            reply_markup=admin_keyboard(app_id)
        )

        for file_id in photos:
            await context.bot.send_photo(
                ADMIN_ID,
                file_id,
                caption=f"Заявка №{app_id}"
            )

    context.user_data.clear()

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("Нет доступа.", show_alert=True)
        return

    action, app_id_text = query.data.split(":")
    app_id = int(app_id_text)

    if action == "work":
        status = "В работе"
        client_text = (
            f"Заявка №{app_id}: мы взяли её в работу. "
            "Специалист свяжется с вами."
        )
    elif action == "reject":
        status = "Отказ"
        client_text = (
            f"По заявке №{app_id} пока не можем сделать предложение. "
            "Спасибо за обращение."
        )
    elif action == "offer":
        context.user_data["offer_app_id"] = app_id
        context.user_data["state"] = "admin_offer"
        await query.message.reply_text(
            f"Введите цену предложения для заявки №{app_id} в рублях."
        )
        return
    else:
        return

    client_id = update_status(app_id, status)

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Статус заявки №{app_id}: {status}")

    if client_id:
        await context.bot.send_message(client_id, client_text)

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("state") != "admin_offer":
        return

    price = update.message.text.strip()
    app_id = context.user_data.get("offer_app_id")
    if not app_id:
        return

    client_id = update_status(app_id, "Предложение отправлено")

    await update.message.reply_text(
        f"💰 Предложение по заявке №{app_id}: {price} ₽ отправлено клиенту."
    )

    if client_id:
        await context.bot.send_message(
            client_id,
            f"💰 *Предварительное предложение*\n\n"
            f"По заявке №{app_id} мы готовы предложить *{price} ₽* за автомобиль.\n\n"
            "Для окончательной оценки может потребоваться осмотр автомобиля.",
            parse_mode="Markdown"
        )

    context.user_data.clear()

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN.")
    if not ADMIN_ID:
        raise RuntimeError("Не задан ADMIN_ID.")

    db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_callback))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler), group=1)

    print("АвтоВыкуп запущен.")
    app.run_polling()

if __name__ == "__main__":
    main()