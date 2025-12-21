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

# Environment Variables Load Karein
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
MONGO_URL = os.getenv('MONGO_URL')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# MongoDB Setup
db_client = pymongo.MongoClient(MONGO_URL)
db = db_client['report_bot_db']
sessions_col = db['sessions']

# --- COMMAND: /make_config [string_session] ---
# Isse aap naye accounts bot mein add karenge
async def make_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/make_config [STRING_SESSION_YAHAN_DALEIN]`")
        return

    session_str = context.args[0]
    await update.message.reply_text("⏳ Session check ho raha hai...")
    
    try:
        # Telethon client se check karna ki session working hai ya nahi
        temp_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await temp_client.connect()
        
        if await temp_client.is_user_authorized():
            me = await temp_client.get_me()
            # Database mein save karna
            if not sessions_col.find_one({"session": session_str}):
                sessions_col.insert_one({
                    "session": session_str, 
                    "user_name": me.first_name,
                    "user_id": me.id
                })
                await update.message.reply_text(f"✅ Account Added: {me.first_name} (ID: {me.id})")
            else:
                await update.message.reply_text("⚠️ Ye session pehle se database mein hai.")
        else:
            await update.message.reply_text("❌ Session expire ho chuka hai ya galat hai.")
        
        await temp_client.disconnect()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# --- COMMAND: /attack [Username/Link] ---
# Isse sabhi saved accounts se report jayegi
async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: `/attack @target_username`")
        return

    target = context.args[0]
    all_sessions = list(sessions_col.find())
    
    if not all_sessions:
        await update.message.reply_text("❌ Database khali hai! Pehle /make_config se accounts add karein.")
        return

    await update.message.reply_text(f"🚀 Attack shuru! {len(all_sessions)} accounts se report bhej raha hoon...")

    success = 0
    for data in all_sessions:
        try:
            client = TelegramClient(StringSession(data['session']), API_ID, API_HASH)
            await client.connect()
            
            # Target ko report karna
            peer = await client.get_entity(target)
            await client(ReportRequest(
                peer=peer,
                id=[1], 
                reason=InputReportReasonChildAbuse(), # Sabse fast action ke liye
                message="Violating safety terms and spreading CSAM content."
            ))
            success += 1
            await client.disconnect()
            await asyncio.sleep(2) # Flood avoid karne ke liye chhota delay
        except Exception as e:
            logging.error(f"Account failed: {e}")
            continue

    await update.message.reply_text(f"🏁 Attack Finished!\n✅ Successful Reports: {success}/{len(all_sessions)}")

# --- COMMAND: /status ---
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    count = sessions_col.count_documents({})
    await update.message.reply_text(f"📊 Total Active Accounts: {count}")

# Main Engine
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("make_config", make_config))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    
    print("Bot chalu hai... Admin ID se commands dein.")
    app.run_polling()

if __name__ == '__main__':
    main()
