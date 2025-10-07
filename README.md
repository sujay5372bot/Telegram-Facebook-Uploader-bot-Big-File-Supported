📦 Telegram → Facebook Page Large Video Uploader Bot

🧠 Overview

This bot automatically uploads videos sent on Telegram to your Facebook Page — including large videos up to 1 GB+ using the Facebook Resumable Upload API.
It’s built in Python using python-telegram-bot and requests, and deployable on Koyeb as a background worker.


---

🚀 Features

✅ Upload videos from Telegram directly to your Facebook Page
✅ Supports large video files (up to 4 GB)
✅ Adds custom caption from Telegram
✅ Uses Facebook’s official Resumable Upload API
✅ 100% deployable on Koyeb (no local hosting needed)


---

🧩 Project Structure

telegram_facebook_uploader/
│
├── bot.py
├── requirements.txt
├── Procfile
└── README.md


---

⚙️ Environment Variables

Set these in Koyeb Dashboard → Settings → Environment Variables

Variable	Description

TELEGRAM_BOT_TOKEN	Token from @BotFather
FB_ACCESS_TOKEN	Facebook Graph API Page access token
FB_PAGE_ID	Your Facebook Page ID


> 💡 Tip: Use a long-lived Page access token from Graph API Explorer.




---

📦 Requirements

python-telegram-bot==20.6
requests
python-dotenv


---

🧠 How It Works

1. User sends a video file to the bot on Telegram.


2. The bot downloads the file temporarily.


3. The bot uploads it to your Facebook Page using the resumable upload process (start → transfer → finish).


4. The bot replies with confirmation and Facebook video ID.




---

▶️ Local Run (optional)

pip install -r requirements.txt
python bot.py


---

☁️ Deploy on Koyeb

1️⃣ Push to GitHub

Upload this folder to a new GitHub repository.

2️⃣ Create App on Koyeb

Go to Koyeb Dashboard

Click Create App

Select your GitHub repo

Choose Service Type: Worker

Add all environment variables

Deploy 🚀


3️⃣ Logs

Check logs in Koyeb to verify successful video uploads:

Started upload session: 123456789
Uploaded chunk: 2097152 / 1048576000
Upload finished: {'success': True, 'video_id': '987654321'}


---

⚠️ Notes

Facebook may take a few minutes to process videos after upload.

If you see "Invalid OAuth access token", regenerate your Page Access Token.

Temporary downloaded files are auto-deleted after upload.



---

🧑‍💻 Credits

Developed by SUJAY 😎 (based on Facebook Graph API + python-telegram-bot).
Deployed on Koyeb Cloud.


