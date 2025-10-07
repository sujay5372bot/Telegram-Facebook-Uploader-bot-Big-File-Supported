import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")

FB_API_BASE = "https://graph-video.facebook.com/v19.0"

def facebook_resumable_upload(video_path, caption):
    # Step 1: Start the upload session
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

    print("Started upload session:", upload_session_id)

    # Step 2: Upload chunks
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
            print(f"Uploaded chunk: {start_offset}/{file_size}")

    # Step 3: Finish upload
    finish_params = {
        "upload_phase": "finish",
        "upload_session_id": upload_session_id,
        "access_token": FB_ACCESS_TOKEN,
        "description": caption
    }
    finish_res = requests.post(start_url, data=finish_params).json()
    print("Upload finished:", finish_res)
    return finish_res

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("❌ Please send a valid video.")
        return

    file = await context.bot.get_file(video.file_id)
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{video.file_unique_id}.mp4"
    await file.download_to_drive(file_path)
    caption = update.message.caption or "Uploaded via Telegram Bot"

    await update.message.reply_text("📤 Uploading to Facebook... Please wait (large file).")
    fb_response = facebook_resumable_upload(file_path, caption)
    await update.message.reply_text(f"✅ Uploaded to Facebook!\nResponse: {fb_response}")
    os.remove(file_path)

app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))

print("🤖 Bot running — Ready for large Facebook video uploads")
app.run_polling()
