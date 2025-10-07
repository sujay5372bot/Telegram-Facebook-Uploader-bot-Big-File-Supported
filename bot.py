import os
import json
import random
import string
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Telegram ID of admin

USERS_FILE = "users.json"
KEYS_FILE = "premium_keys.json"
FB_API_BASE = "https://graph-video.facebook.com/v19.0"

# ---- Helper functions ----
def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(data, file_path):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

users = load_json(USERS_FILE)
premium_keys = load_json(KEYS_FILE)

def generate_ref_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

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
    ref_code = generate_ref_code()

    if user_id not in users:
        referred_by = None
        # Check if referral code provided
        if context.args:
            input_code = context.args[0]
            for uid, udata in users.items():
                if udata.get("ref_code") == input_code:
                    users[uid]["referrals"] += 1
                    if users[uid]["referrals"] >= 5:
                        users[uid]["is_premium"] = True
                    referred_by = uid
                    break
        users[user_id] = {
            "is_premium": False,
            "uploads": 0,
            "referrals": 0,
            "ref_code": ref_code,
            "referred_by": referred_by
        }
        save_json(users, USERS_FILE)

    msg = "👋 Welcome! Send a video to upload to Facebook Page.\n"
    if users[user_id]["is_premium"]:
        msg += "💎 You are Premium. Unlimited uploads!"
    else:
        msg += "⚠️ Free user. Max 200MB video. Invite friends to get Premium!"
    msg += f"\nYour referral code: {users[user_id]['ref_code']}"
    await update.message.reply_text(msg)

async def myref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in users:
        u = users[user_id]
        await update.message.reply_text(f"💡 Your referral code: {u['ref_code']}\nReferrals: {u['referrals']}")
    else:
        await update.message.reply_text("Use /start first.")

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if not context.args:
        return await update.message.reply_text("Usage: /redeem <key>")
    key = context.args[0]
    if key in premium_keys:
        users[user_id]["is_premium"] = True
        save_json(users, USERS_FILE)
        # Remove key after use
        premium_keys.pop(key)
        save_json(premium_keys, KEYS_FILE)
        await update.message.reply_text("✅ Premium activated via secret key!")
    else:
        await update.message.reply_text("❌ Invalid key.")

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Unauthorized")
    if not context.args:
        return await update.message.reply_text("Usage: /addpremium <user_id>")
    user_id = context.args[0]
    users[user_id]["is_premium"] = True
    save_json(users, USERS_FILE)
    await update.message.reply_text(f"✅ User {user_id} upgraded to Premium.")

async def generate_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Unauthorized")
    key = ''.join(random.choices(string.ascii_letters+string.digits, k=8))
    premium_keys[key] = True
    save_json(premium_keys, KEYS_FILE)
    await update.message.reply_text(f"✅ Generated key: {key}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    video = update.message.video or update.message.document

    if user_id not in users:
        users[user_id] = {"is_premium": False, "uploads": 0, "referrals":0, "ref_code":generate_ref_code(), "referred_by":None}
        save_json(users, USERS_FILE)

    # Free user restriction
    if not users[user_id]["is_premium"] and video.file_size > 200*1024*1024:
        return await update.message.reply_text("❌ Free users max 200MB. Upgrade to Premium 💎.")

    file = await context.bot.get_file(video.file_id)
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{video.file_unique_id}.mp4"
    await file.download_to_drive(file_path)
    caption = update.message.caption or "Uploaded via Telegram Bot"

    await update.message.reply_text("📤 Uploading to Facebook... please wait (large file).")
    fb_response = facebook_resumable_upload(file_path, caption)
    await update.message.reply_text(f"✅ Uploaded!\nResponse: {fb_response}")

    users[user_id]["uploads"] += 1
    save_json(users, USERS_FILE)
    os.remove(file_path)

# ---- Bot Setup ----
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("myref", myref))
app.add_handler(CommandHandler("redeem", redeem))
app.add_handler(CommandHandler("addpremium", add_premium))
app.add_handler(CommandHandler("generatekey", generate_key))
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

print("🤖 Premium uploader bot with Referral, Payment, Key system running...")
app.run_polling()
