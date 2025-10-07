import os
import json
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Your Telegram ID

USERS_FILE = "users.json"
FB_API_BASE = "https://graph-video.facebook.com/v19.0"

# ---- Helper: Load/Save Users ----
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

users = load_users()

# ---- Facebook Upload Function ----
def facebook_resumable_upload(video_path, caption):
    start_url = f"{FB_API_BASE}/{FB_PAGE_ID}/videos"
    start_params = {
        "upload_phase": "start",
        "access_token": FB_ACCESS_TOKEN,
        "file_size": os.path.getsize(video_path)
    }
    start_res = requests.post(start_url, data=start_params).json()

    upload_session_id = start_res["upload_session_id"]
    upload_url = start_res["upload_url"]
    start_offset = int(start_res["start_offset"])
    end_offset = int(start_res["end_offset"])
    file_size = os.path.getsize(video_path)

    with open(video_path, "rb") as f:
        while start_offset < file_size:
            f.seek(start_offset)
            chunk = f.read(end_offset - start_offset)
            files = {'video_file_chunk': chunk}
            upload_params = {
                "upload_phase": "transfer",
                "start_offset": start_offset,
                "upload_session_id": upload_session_id,
                "access_token": FB_ACCESS_TOKEN
            }
            upload_res = requests.post(upload_url, files=files, data=upload_params).json()
            start_offset = int(upload_res["start_offset"])
            end_offset = int(upload_res["end_offset"])

    finish_params = {
        "upload_phase": "finish",
        "upload_session_id": upload_session_id,
        "access_token": FB_ACCESS_TOKEN,
        "description": caption
    }
    finish_res = requests.post(start_url, data=finish_params).json()
    return finish_res

# ---- Commands ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in users:
        users[user_id] = {"is_premium": False, "uploads": 0}
        save_users(users)
    msg = "👋 Welcome! Send a video to upload it to Facebook Page.\n"
    if users[user_id]["is_premium"]:
        msg += "💎 You are a Premium user. Enjoy unlimited uploads!"
    else:
        msg += "⚠️ You are a Free user. Max size: 200MB."
    await update.message.reply_text(msg)

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ You are not authorized.")
    if not context.args:
        return await update.message.reply_text("Usage: /addpremium <user_id>")
    user_id = context.args[0]
    users[user_id] = {"is_premium": True, "uploads": 0}
    save_users(users)
    await update.message.reply_text(f"✅ User {user_id} upgraded to Premium!")

# ---- Handle Video ----
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    video = update.message.video or update.message.document

    if user_id not in users:
        users[user_id] = {"is_premium": False, "uploads": 0}
        save_users(users)

    # Free user restriction
    if not users[user_id]["is_premium"] and video.file_size > 200 * 1024 * 1024:
        return await update.message.reply_text("❌ Free users can only upload videos under 200MB.\nUpgrade to Premium 💎.")

    file = await context.bot.get_file(video.file_id)
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{video.file_unique_id}.mp4"
    await file.download_to_drive(file_path)
    caption = update.message.caption or "Uploaded via Telegram Bot"

    await update.message.reply_text("📤 Uploading to Facebook... please wait.")
    fb_response = facebook_resumable_upload(file_path, caption)
    await update.message.reply_text(f"✅ Uploaded to Facebook!\nResponse: {fb_response}")

    users[user_id]["uploads"] += 1
    save_users(users)
    os.remove(file_path)

# ---- Bot Setup ----
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addpremium", add_premium))
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

print("🤖 Premium uploader bot running on Koyeb...")
app.run_polling()
