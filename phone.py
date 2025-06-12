import os
import time
import httpx
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN") or "7431786870:AAGoMeKIkd2n5kuO7RKcxBKb_uEtyC-BWZg"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") or " https://ifpkqljiba.a.pinggy.link/webhook"
app = Flask(__name__)

# --- CACHING & SPAM PROTECTION ---
COUNTRIES_CACHE = None
COUNTRIES_CACHE_TIME = 0
CACHE_DURATION = 300
USER_LAST_MESSAGE = {}
SPAM_INTERVAL = 2

# --- TELEGRAM BOT SETUP ---
application = Application.builder().token(BOT_TOKEN).build()
PREMIUM_EMOJI = "💎"
FREE_EMOJI = "🆓"
WELCOME_MSG = (
    f"{PREMIUM_EMOJI} Welcome to Premium OTP Bot!\n"
    "\n"
    "📲 Instantly receive OTPs for account verifications.\n"
    "🌍 Choose a country, select a number, and view SMS (OTP) in real time!\n"
    "\n"
    "✨ Tap a button below to get started!"
)

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Countries", callback_data="menu_countries")],
        [InlineKeyboardButton("📊 Dashboard", callback_data="menu_dashboard")],
        [InlineKeyboardButton(f"{PREMIUM_EMOJI} Upgrade", callback_data="menu_premium")]
    ])

# --- /start HANDLER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(WELCOME_MSG, reply_markup=main_menu())

# --- COUNTRIES MENU HANDLER ---
async def menu_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    now = time.time()
    if now - USER_LAST_MESSAGE.get(user_id, 0) < SPAM_INTERVAL:
        await query.answer("⏳ Please wait before sending another command.", show_alert=True)
        return
    USER_LAST_MESSAGE[user_id] = now
    global COUNTRIES_CACHE, COUNTRIES_CACHE_TIME
    if COUNTRIES_CACHE is None or time.time() - COUNTRIES_CACHE_TIME > CACHE_DURATION:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://sms24.me/api/country")
            resp.raise_for_status()
            data = resp.json()
            COUNTRIES_CACHE = [{"code": c["code"], "name": c["name"]} for c in data["countries"]]
            COUNTRIES_CACHE.sort(key=lambda x: x["name"])
            COUNTRIES_CACHE_TIME = time.time()
    countries = COUNTRIES_CACHE
    buttons = [
        [InlineKeyboardButton(f"{PREMIUM_EMOJI if i%3==0 else '🌐'} {c['name']}", callback_data=f"country_{c['code']}")]
        for i, c in enumerate(countries[:15])
    ]
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")])
    await query.edit_message_text("🌍 Select a country:", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# --- NUMBERS MENU HANDLER ---
async def country_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    country_code = query.data.split("_", 1)[1]
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://sms24.me/api/number/{country_code}")
        resp.raise_for_status()
        numbers = resp.json()["numbers"]
    if not numbers:
        await query.edit_message_text(
            "❌ No numbers available for this country.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="menu_countries")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")]
            ]),
            parse_mode="HTML"
        )
        return
    buttons = [
        [InlineKeyboardButton(f"📱 {n['number']}", callback_data=f"number_{n['id']}")]
        for n in numbers[:10]
    ]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="menu_countries")])
    await query.edit_message_text(
        "📱 Select a number for OTP:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML"
    )

# --- SMS/OTP DISPLAY HANDLER ---
async def number_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    number_id = query.data.split("_", 1)[1]
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://sms24.me/api/messages/{number_id}")
        resp.raise_for_status()
        sms_list = resp.json()["messages"]
    if not sms_list:
        await query.edit_message_text(
            "✉️ No SMS received yet. Try again later.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"number_{number_id}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")]
            ]),
            parse_mode="HTML"
        )
        return
    text = "✉️ Latest OTPs for this number:\n\n"
    for sms in sms_list[:5]:
        text += (
            f"From: {sms['from']}\n"
            f"Text: {sms['text']}\n"
            f"Date: {sms['date']}\n"
            "━━━━━━━━━━━━━━\n"
        )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"number_{number_id}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")]
        ]),
        parse_mode="HTML"
    )

# --- MAIN MENU HANDLER ---
async def menu_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(WELCOME_MSG, reply_markup=main_menu(), parse_mode="HTML")

# --- DASHBOARD HANDLER (PREMIUM STYLE DEMO) ---
async def menu_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    badge = PREMIUM_EMOJI + " Premium" if is_premium(user_id) else FREE_EMOJI + " Free"
    text = (
        f"📊 Your Dashboard\n"
        f"Status: {badge}\n"
        "Favorites: Coming soon..."
    )
    buttons = [
        [InlineKeyboardButton("🌍 Countries", callback_data="menu_countries")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# --- PREMIUM UPGRADE HANDLER (DEMO) ---
async def menu_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        f"{PREMIUM_EMOJI} Upgrade to Premium\n"
        "\n"
        "• Access VIP numbers\n"
        "• Higher limits\n"
        "• Priority support\n"
        "\n"
        "Contact @YourSupport for upgrade"
    )
    buttons = [
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

def is_premium(user_id):
    # Replace with your premium user logic
    return False

# --- REGISTER HANDLERS ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(menu_countries, pattern="^menu_countries$"))
application.add_handler(CallbackQueryHandler(menu_main, pattern="^menu_main$"))
application.add_handler(CallbackQueryHandler(country_selected, pattern="^country_"))
application.add_handler(CallbackQueryHandler(number_selected, pattern="^number_"))
application.add_handler(CallbackQueryHandler(menu_dashboard, pattern="^menu_dashboard$"))
application.add_handler(CallbackQueryHandler(menu_premium, pattern="^menu_premium$"))

# --- FLASK WEBHOOK ENDPOINT ---
import asyncio
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.get_event_loop().run_until_complete(application.update_queue.put(update))
    return "ok"

def set_webhook():
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(url, data={"url": WEBHOOK_URL})
    print("Webhook set:", response.json())

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=8000)
