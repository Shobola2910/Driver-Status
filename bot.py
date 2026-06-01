import logging
import os
from datetime import datetime

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN")
SHEET_ID   = os.getenv("SHEET_ID")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")   # Flask server URL (HTTPS)

# Conversation states
COMPANY, DRIVER_NAME, STATUS, REASON = range(4)

STATUS_CONFIG = {
    "GOOD":     {"emoji": "\U0001f7e2", "color": (183, 225, 205)},
    "MONITOR":  {"emoji": "\U0001f7e1", "color": (255, 242, 204)},
    "RED FLAG": {"emoji": "\U0001f534", "color": (255, 199, 206)},
}

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def main_menu_keyboard():
    rows = []
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(
            "\U0001f310 Web App ochish",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )])
    rows += [
        [InlineKeyboardButton("➕ Add Driver",  callback_data="menu_add")],
        [InlineKeyboardButton("\U0001f4cb Driver List", callback_data="menu_list")],
        [InlineKeyboardButton("\U0001f4ca Stats",       callback_data="menu_stats")],
    ]
    return InlineKeyboardMarkup(rows)


# ── Google Sheets helpers ─────────────────────────────────────────────────────

def get_sheet():
    try:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        logger.error(f"Google Sheets ulanishda xato: {e}")
        raise


def append_driver(company: str, name: str, status_key: str, reason: str):
    sheet = get_sheet()
    cfg = STATUS_CONFIG[status_key]
    status_display = f"{cfg['emoji']} {status_key}"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    row = [status_display, name, company, status_key, reason, date_str]
    sheet.append_row(row, value_input_option="USER_ENTERED")

    last_row = len(sheet.get_all_values())
    r, g, b = cfg["color"]
    sheet.spreadsheet.batch_update({"requests": [{
        "repeatCell": {
            "range": {
                "sheetId": sheet.id,
                "startRowIndex": last_row - 1,
                "endRowIndex": last_row,
                "startColumnIndex": 0,
                "endColumnIndex": 6,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": r/255, "green": g/255, "blue": b/255},
                    "textFormat": {"bold": status_key == "RED FLAG"},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    }]})


def get_drivers_by_status(status_key: str) -> list:
    sheet = get_sheet()
    rows = sheet.get_all_records()
    return [r for r in rows if r.get("STATUS_KEY") == status_key]


def get_all_stats() -> dict:
    sheet = get_sheet()
    rows = sheet.get_all_records()
    stats = {"GOOD": 0, "MONITOR": 0, "RED FLAG": 0, "total": len(rows)}
    for r in rows:
        key = r.get("STATUS_KEY", "")
        if key in stats:
            stats[key] += 1
    return stats


# ── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "\U0001f69b *Algo Group — Driver Status Bot*\n\nQuyidagi amalni tanlang:"
    if WEBAPP_URL:
        text += "\n\n\U0001f310 *Web App* — to'liq interfeys, filter va boshqalar"
    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_add":
        await query.edit_message_text("\U0001f3e2 *Company nomini kiriting:*", parse_mode="Markdown")
        return COMPANY
    elif query.data == "menu_list":
        await show_status_selector(query)
    elif query.data == "menu_stats":
        await show_stats(query)
    return ConversationHandler.END


# ── Add Driver conversation ───────────────────────────────────────────────────

async def get_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["company"] = update.message.text.strip()
    await update.message.reply_text("\U0001f464 *Driver to'liq ismini kiriting:*", parse_mode="Markdown")
    return DRIVER_NAME


async def get_driver_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["driver_name"] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("\U0001f7e2 GOOD — Yaxshi holat",        callback_data="status_GOOD")],
        [InlineKeyboardButton("\U0001f7e1 MONITOR — Kuzatish kerak",   callback_data="status_MONITOR")],
        [InlineKeyboardButton("\U0001f534 RED FLAG — Darhol e'tibor!", callback_data="status_RED FLAG")],
    ]
    await update.message.reply_text(
        "\U0001f4cc *Statusni tanlang:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return STATUS


async def get_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_key = query.data.replace("status_", "")
    context.user_data["status"] = status_key
    cfg = STATUS_CONFIG[status_key]
    await query.edit_message_text(
        f"Status: *{cfg['emoji']} {status_key}*\n\n✏️ *Sabab / izoh kiriting:*",
        parse_mode="Markdown",
    )
    return REASON


async def get_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text.strip()
    ud = context.user_data
    company     = ud.get("company", "")
    driver_name = ud.get("driver_name", "")
    status_key  = ud.get("status", "GOOD")
    cfg = STATUS_CONFIG[status_key]

    try:
        append_driver(company, driver_name, status_key, reason)
        await update.message.reply_text(
            f"✅ *Driver muvaffaqiyatli qo'shildi!*\n\n"
            f"\U0001f3e2 Company: {company}\n"
            f"\U0001f464 Driver: {driver_name}\n"
            f"\U0001f4cc Status: {cfg['emoji']} {status_key}\n"
            f"\U0001f4dd Sabab: {reason}\n\n"
            f"Quyidagi amalni tanlang:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Driver qo'shishda xato: {e}")
        await update.message.reply_text(
            "❌ Xato yuz berdi. Qayta urinib ko'ring.",
            reply_markup=main_menu_keyboard(),
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


# ── Driver List ───────────────────────────────────────────────────────────────

async def show_status_selector(query):
    try:
        stats = get_all_stats()
    except Exception:
        await query.edit_message_text("❌ Ma'lumot olishda xato yuz berdi.")
        return

    keyboard = [
        [InlineKeyboardButton(f"\U0001f7e2 GOOD ({stats['GOOD']})",         callback_data="list_GOOD")],
        [InlineKeyboardButton(f"\U0001f7e1 MONITOR ({stats['MONITOR']})",   callback_data="list_MONITOR")],
        [InlineKeyboardButton(f"\U0001f534 RED FLAG ({stats['RED FLAG']})", callback_data="list_RED FLAG")],
        [InlineKeyboardButton("\U0001f3e0 Bosh menyu",                      callback_data="menu_home")],
    ]
    await query.edit_message_text(
        "\U0001f4cb *Driver ro'yxati — Status tanlang:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_home":
        await query.edit_message_text(
            "\U0001f69b *Algo Group — Driver Status Bot*\n\nQuyidagi amalni tanlang:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    if data.startswith("list_"):
        status_key = data[5:]
        try:
            drivers = get_drivers_by_status(status_key)
        except Exception:
            await query.edit_message_text("❌ Ma'lumot olishda xato.")
            return

        cfg = STATUS_CONFIG[status_key]
        if not drivers:
            keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="back_list")]]
            await query.edit_message_text(
                f"{cfg['emoji']} {status_key} statusida hech qanday driver yo'q.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        keyboard = []
        for i, d in enumerate(drivers):
            name    = d.get("DRIVER NAME", "Noma'lum")
            company = d.get("COMPANY NAME", "")
            keyboard.append([InlineKeyboardButton(
                f"{name} — {company}",
                callback_data=f"driver_{status_key}_{i}",
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back_list")])

        context.user_data["drivers_cache"] = drivers
        await query.edit_message_text(
            f"{cfg['emoji']} *{status_key} driverlar ro'yxati:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data.startswith("driver_"):
        parts      = data.split("_", 2)
        status_key = parts[1]
        idx        = int(parts[2])
        drivers    = context.user_data.get("drivers_cache", [])

        if idx >= len(drivers):
            await query.edit_message_text("❌ Driver topilmadi.")
            return

        d   = drivers[idx]
        cfg = STATUS_CONFIG.get(status_key, {})
        text = (
            f"\U0001f464 *{d.get('DRIVER NAME', '—')}*\n"
            f"\U0001f3e2 Company: {d.get('COMPANY NAME', '—')}\n"
            f"\U0001f4cc Status: {cfg.get('emoji', '')} {status_key}\n"
            f"\U0001f4dd Sabab: {d.get('REASON / NOTES', '—')}\n"
            f"\U0001f4c5 Sana: {d.get('DATE', '—')}"
        )
        keyboard = [
            [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"list_{status_key}")],
            [InlineKeyboardButton("\U0001f3e0 Bosh menyu", callback_data="menu_home")],
        ]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    elif data == "back_list":
        await show_status_selector(query)


# ── Stats ─────────────────────────────────────────────────────────────────────

async def show_stats(query):
    try:
        stats = get_all_stats()
    except Exception:
        await query.edit_message_text("❌ Statistika olishda xato yuz berdi.")
        return

    total = stats["total"]

    def bar(count, t, length=10):
        if t == 0: return "░" * length
        filled = round((count / t) * length)
        return "█" * filled + "░" * (length - filled)

    text = (
        f"\U0001f4ca *Algo Group — Driver Statistikasi*\n\n"
        f"\U0001f465 Jami driverlar: *{total}*\n\n"
        f"\U0001f7e2 GOOD:     *{stats['GOOD']}*  {bar(stats['GOOD'], total)}\n"
        f"\U0001f7e1 MONITOR:  *{stats['MONITOR']}*  {bar(stats['MONITOR'], total)}\n"
        f"\U0001f534 RED FLAG: *{stats['RED FLAG']}*  {bar(stats['RED FLAG'], total)}\n"
    )
    keyboard = [[InlineKeyboardButton("\U0001f3e0 Bosh menyu", callback_data="menu_home")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")
    if not SHEET_ID:
        raise ValueError("SHEET_ID topilmadi!")

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(main_menu_callback, pattern="^menu_add$")],
        states={
            COMPANY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_company)],
            DRIVER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_driver_name)],
            STATUS:      [CallbackQueryHandler(get_status, pattern="^status_")],
            REASON:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_reason)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(list_callback, pattern="^(list_|driver_|back_|menu_home)"))

    logger.info("Algo Group Driver Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
