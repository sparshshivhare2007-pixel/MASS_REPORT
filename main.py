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

# MongoDB Setup
try:
    db_client = pymongo.MongoClient(MONGO_URL)
    # Database ka naam 'report_bot_db' hai, aap ise change bhi kar sakte hain
    db = db_client['report_bot_db'] 
    # Collection ka naam 'sessions' hai
    sessions_col = db['sessions']
    logging.info("MongoDB connected successfully!")
except Exception as e:
    logging.error(f"MongoDB Connection Error: {e}")

# Admin Session Tracking Mode
ADDING_SESSIONS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        "🛠️ **Mass Report Admin Panel**\n\n"
        "📜 **Commands List:**\n"
        "🔹 `/make_config` - Sessions add karna shuru karein\n"
        "🔹 `/attack @target` - Mass report attack start karein\n"
        "🔹 `/status` - Dekhein kitne accounts DB mein hain\n"
        "🔹 `/clean_db` - Poora database saaf karne ke liye"
    )

# --- SESSION HANDLING ---
async def make_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    ADDING_SESSIONS[update.effective_user.id] = True
    await update.message.reply_text("📥 **Mode: Session Adding ON**\n\nAb String Sessions paste karke bhejte rahein. Khatam hone par `/done` likh kar band karein.")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID or user_id not in ADDING_SESSIONS: return

    text = update.message.text.strip()

    if text.lower() == '/done':
        del ADDING_SESSIONS[user_id]
        count = sessions_col.count_documents({})
        await update.message.reply_text(f"✅ Mode OFF. Database mein total **{count}** accounts hain.")
        return

    # Validation and Storage
    try:
        client = TelegramClient(StringSession(text), API_ID, API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            # Duplicate check
            if not sessions_col.find_one({"session": text}):
                sessions_col.insert_one({"session": text, "user": me.first_name, "id": me.id})
                await update.message.reply_text(f"🔹 Saved: {me.first_name} (@{me.username or 'No Username'}) ✅")
            else:
                await update.message.reply_text("⚠️ Ye session pehle se database mein hai.")
        else:
            await update.message.reply_text("❌ Ye session valid nahi hai.")
        await client.disconnect()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}...")

# --- MASS REPORT LOGIC ---
async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/attack @target_username` ya link")
        return

    target = context.args[0]
    all_sessions = list(sessions_col.find())
    
    if not all_sessions:
        await update.message.reply_text("❌ Database khali hai! Pehle accounts add karein.")
        return

    await update.message.reply_text(f"🚀 **Attack Started on {target}**\nUsing {len(all_sessions)} accounts...")

    success = 0
    for data in all_sessions:
        try:
            client = TelegramClient(StringSession(data['session']), API_ID, API_HASH)
            await client.connect()
            peer = await client.get_entity(target)

            # Report 1: Profile Level (Child Abuse)
            await client(ReportRequest(
                peer=peer, id=[0], 
                reason=InputReportReasonChildAbuse(), 
                message="Violating safety terms and spreading CSAM."
            ))
            
            # Report 2: Message Level (Scam/Spam)
            msgs = await client.get_messages(peer, limit=1)
            if msgs:
                await client(ReportRequest(
                    peer=peer, id=[msgs[0].id], 
                    reason=InputReportReasonSpam(), 
                    message="Scamming activity."
                ))
            
            success += 1
            await client.disconnect()
            await asyncio.sleep(2) # Speed balanced with safety
        except Exception:
            continue

    await update.message.reply_text(f"🏁 **Attack Finished!**\n✅ Reports successfully sent from {success} accounts.")

# --- UTILS ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    count = sessions_col.count_documents({})
    await update.message.reply_text(f"📊 Current Accounts in DB: **{count}**")

async def clean_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    sessions_col.delete_many({})
    await update.message.reply_text("🗑️ Database successfully cleared!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("make_config", make_config))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clean_db", clean_db))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    print("Bot is alive...")
    app.run_polling()

if __name__ == '__main__':
    main()
