from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import *
from database import add_user, increment_task_count, decrement_task_count, get_task_count, is_premium, set_premium, get_user_plan

try:
    from moviepy.editor import VideoFileClip
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    print("Error importing required modules: ", e)
    raise

# State management for tracking user actions
user_states = {}
user_videos = {}

app = Client("MultitaskingBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
def start(client, message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Add user to the database
    add_user(user_id, username)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Help", callback_data="help"),
         InlineKeyboardButton("Updates Channel", url=f"https://t.me/{UPDATES_CHANNEL}")],
        [InlineKeyboardButton("About", callback_data="about")]
    ])

    message.reply_text(
        f"""✨ **Welcome, {username}!** ✨

**This bot helps you with:**
- **File Conversion (MP4 <-> MKV)**
- **File Renaming**
- **Screenshot Generation**

Join the updates channel: [Updates Channel](https://t.me/{UPDATES_CHANNEL})
        """,
        reply_markup=keyboard
    )
    app.send_message(LOG_CHANNEL_ID, f"**New User Alert!**\nUser: `{username}`\nID: `{user_id}`")

@app.on_message(filters.command("help") & filters.private)
def help_command(client, message):
    message.reply_text(
        """**HELP MENU** 📖

Here is how you can use this bot:

1️⃣ **Send a Video**: Send a video file to the bot to access the following features:
   - Generate Screenshots
   - Rename the Video
   - Convert Video Format (MP4 <-> MKV)

2️⃣ **Subscription Plans**:
   - Free users: Limited to 100 tasks per month.
   - Premium users: Unlimited tasks for ₹99/month.

3️⃣ **Commands**:
   - `/start`: Welcome message and menu.
   - `/help`: Display this help message.
   - `/myplan`: Check your subscription plan.
   - `/plans`: View available subscription plans.
   - `/addpremium <user_id> <days>`: Add premium to a user (Admin only).
   - `/broadcast <message>`: Broadcast a message to all users (Admin only).

**Note**:
- Tasks are limited to 10 concurrent tasks per user.
- Join our [Updates Channel](https://t.me/{UPDATES_CHANNEL}) for news and updates.

For support, contact [Developer](https://t.me/{DEVELOPER}).
        """,
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex("about"))
def about_command(client, callback_query):
    callback_query.message.reply_text(
        """**ABOUT THIS BOT** 🤖

This is a **Multitasking Bot** designed to:
- Convert video formats (MP4 <-> MKV)
- Rename videos with custom names
- Generate video screenshots

**Features**:
- Free users: 100 tasks/month
- Premium users: Unlimited tasks for ₹99/month

**Developer**: [Mr_provider](https://t.me/{DEVELOPER})
**Bot Version**: 1.0.0
**Updates Channel**: [tcp_bots](https://t.me/{UPDATES_CHANNEL})

Thank you for using the bot! 🌟
        """,
        disable_web_page_preview=True
    )

@app.on_message(filters.video & filters.private)
def handle_video(client, message):
    user_id = message.from_user.id
    video_file = message.video

    # Save the video file_id for later reference
    user_videos[user_id] = video_file.file_id
    user_states[user_id] = "awaiting_screenshot_count"

    message.reply_text("**How many screenshots do you want (Max: 15)?**")

@app.on_message(filters.text & filters.private)
def process_screenshot_count(client, message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == "awaiting_screenshot_count":
        try:
            screenshot_count = int(message.text)
            if screenshot_count > 15:
                message.reply_text("**Please enter a number less than or equal to 15.**")
            else:
                message.reply_text("**Please wait! Your request is being processed...**")

                # Retrieve the video file_id
                video_file_id = user_videos.get(user_id)
                if not video_file_id:
                    message.reply_text("**Error: No video found. Please send the video again.**")
                    return

                # Download the video into memory
                video_bytes = BytesIO()
                app.download_media(video_file_id, file=video_bytes)
                video_bytes.seek(0)
                video = VideoFileClip(video_bytes)

                # Generate screenshots
                duration = video.duration
                interval = duration / screenshot_count
                for i in range(screenshot_count):
                    frame_time = i * interval
                    frame = video.get_frame(frame_time)

                    # Convert frame to image
                    img = Image.fromarray(frame)
                    draw = ImageDraw.Draw(img)

                    # Add watermark
                    watermark_text = "TCP Bots"
                    font = ImageFont.load_default()
                    text_width, text_height = draw.textsize(watermark_text, font=font)
                    x = img.width - text_width - 10
                    y = img.height - text_height - 10
                    draw.text((x, y), watermark_text, fill="white", font=font)

                    # Convert image to BytesIO and send
                    img_bytes = BytesIO()
                    img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)

                    message.reply_photo(img_bytes)

                # Log the request
                app.send_message(LOG_CHANNEL_ID, f"**Screenshots generated for user {user_id}.**")

                message.reply_text(
                    f"**Thank you for using the bot!**\nContact: [tcp_bots](https://t.me/{UPDATES_CHANNEL})",
                    disable_web_page_preview=True
                )

                # Clear user state and video
                user_states.pop(user_id, None)
                user_videos.pop(user_id, None)
        except ValueError:
            message.reply_text("**Invalid input. Please enter a valid number.**")

# Run the bot
if __name__ == "__main__":
    print("Bot Started")
    app.run()
