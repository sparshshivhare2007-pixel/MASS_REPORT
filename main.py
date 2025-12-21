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
from telegram.ext import Application, CommandHandler, ContextTypes

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
MONGO_URL = os.getenv('MONGO_URL')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# MongoDB
db_client = pymongo.MongoClient(MONGO_URL)
db = db_client['mass_report_db']
sessions_col = db['sessions']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("✅ Admin Panel Active.\nCommands: /make_config, /attack, /status")

# --- 1. SESSION ADD KARNA ---
async def make_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/make_config [SESSION]`")
        return

    session_str = context.args[0]
    try:
        temp_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await temp_client.connect()
        if await temp_client.is_user_authorized():
            me = await temp_client.get_me()
            if not sessions_col.find_one({"session": session_str}):
                sessions_col.insert_one({"session": session_str, "user": me.first_name})
                await update.message.reply_text(f"✅ Saved: {me.first_name}")
            else:
                await update.message.reply_text("⚠️ Already exists.")
        await temp_client.disconnect()
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid: {e}")

# --- 2. MASS ATTACK (3 CATEGORIES & 2 REPS PER ACC) ---
async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/attack @target`")
        return

    target = context.args[0]
    all_sessions = list(sessions_col.find())
    
    await update.message.reply_text(f"🚀 Attack started on {target}...\n(2 Reports per account - Child Abuse, Scam, Violence)")

    success = 0
    reasons = [InputReportReasonChildAbuse(), InputReportReasonSpam(), InputReportReasonViolence()]

    for data in all_sessions:
        try:
            client = TelegramClient(StringSession(data['session']), API_ID, API_HASH)
            await client.connect()
            peer = await client.get_entity(target)

            # Report 1: Channel/User level report
            await client(ReportRequest(
                peer=peer, id=[0], 
                reason=reasons[0], # Child Abuse
                message="CSAM and Illegal content found."
            ))

            # Report 2: Message level report (Recent messages)
            msgs = await client.get_messages(peer, limit=1)
            if msgs:
                await client(ReportRequest(
                    peer=peer, id=[msgs[0].id], 
                    reason=reasons[1], # Scam/Spam
                    message="Fraudulent activity and scamming."
                ))

            success += 1
            await client.disconnect()
            await asyncio.sleep(4) # Safety delay
        except:
            continue

    await update.message.reply_text(f"🏁 Done! {success} accounts performed double reporting.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    count = sessions_col.count_documents({})
    await update.message.reply_text(f"📊 Total Accounts: {count}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("make_config", make_config))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    app.run_polling()

if __name__ == '__main__':
    main()
