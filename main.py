from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from config import *
from database import add_user, increment_task_count, decrement_task_count, get_task_count, is_premium, set_premium, get_user_plan

try:
    from moviepy.editor import VideoFileClip
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont
    import os
    import psutil
except ImportError as e:
    print("Error importing required modules: ", e)
    raise

# State management for tracking user actions
user_states = {}
user_videos = {}

app = Client("ScreenshotGeneratorBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
def start(client, message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Check if user is subscribed to the updates channel
    try:
        member = app.get_chat_member(UPDATES_CHANNEL_ID, user_id)
        if not member.status in ["member", "administrator", "creator"]:
            message.reply_text(
                f"**Please join our updates channel to use this bot:** [Join Now](https://t.me/{UPDATES_CHANNEL})",
                disable_web_page_preview=True
            )
            return
    except Exception as e:
        message.reply_text(
            f"**Please join our updates channel to use this bot:** [Join Now](https://t.me/{UPDATES_CHANNEL})",
            disable_web_page_preview=True
        )
        return

    # Add user to the database
    is_new_user = add_user(user_id, username)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Help", callback_data="help"),
         InlineKeyboardButton("Updates Channel", url=f"https://t.me/{UPDATES_CHANNEL}")],
        [InlineKeyboardButton("About", callback_data="about")]
    ])

    message.reply_text(
        f"""✨ **Welcome, {username}!** ✨

**This bot helps you generate screenshots from videos or create sample videos.**

Join the updates channel: [Updates Channel](https://t.me/{UPDATES_CHANNEL})
        """,
        reply_markup=keyboard
    )

    if is_new_user:
        app.send_message(LOG_CHANNEL_ID, f"**New User Alert!**\nUser: `{username}`\nID: `{user_id}`")

@app.on_callback_query(filters.regex("help"))
def help_callback(client, callback_query):
    callback_query.message.edit_text(
        """**HELP MENU** 📖

Here is how you can use this bot:

1️⃣ **Send a Video**: Send a video file to the bot to:
   - Generate Screenshots
   - Create a Sample Video (30 seconds, random section)

2️⃣ **Subscription Plans**:
   - Free users: Limited to 100 tasks per month.
   - Premium users: Unlimited tasks for ₹99/month.

**Commands**:
   - `/start`: Welcome message and menu.
   - `/myplan`: Check your subscription plan.
   - `/plans`: View available subscription plans.

**Note**:
- Join our [Updates Channel](https://t.me/{UPDATES_CHANNEL}) for news and updates.

For support, contact [Developer](https://t.me/{DEVELOPER}).
        """,
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex("about"))
def about_callback(client, callback_query):
    callback_query.message.edit_text(
        """**ABOUT THIS BOT** 🤖

This is a **Screenshot Generator Bot** designed to:
- Generate screenshots from videos
- Create sample videos (30 seconds with watermark)

**Features**:
- Free users: 100 tasks/month
- Premium users: Unlimited tasks for ₹99/month

**Developer**: [Mr_provider](https://t.me/{DEVELOPER})
**Updates Channel**: [tcp_bots](https://t.me/{UPDATES_CHANNEL})

Thank you for using the bot! 🌟
        """,
        disable_web_page_preview=True
    )

@app.on_message(filters.command("plans") & filters.private)
def plans_command(client, message):
    message.reply_text(
        """**PLANS** 💳

1️⃣ **Free Plan**:
   - 100 tasks per month.

2️⃣ **Premium Plan**:
   - Unlimited tasks.
   - ₹99/month.

To subscribe, contact: [Developer](https://t.me/{DEVELOPER}).
        """,
        disable_web_page_preview=True
    )

@app.on_message(filters.command("myplan") & filters.private)
def myplan_command(client, message):
    user_id = message.from_user.id
    plan = get_user_plan(user_id)
    if plan["is_premium"]:
        expiry = plan["expiry"].strftime("%Y-%m-%d %H:%M:%S")
        message.reply_text(f"**You are a Premium user.**\n**Expiry Date:** {expiry}")
    else:
        message.reply_text("**You are on the Free plan.**\nUpgrade to Premium for unlimited access!")

@app.on_message(filters.video & filters.private)
def handle_video(client, message):
    user_id = message.from_user.id
    video_file = message.video

    # Save the video file_id for later reference
    user_videos[user_id] = video_file.file_id
    user_states[user_id] = "awaiting_function_choice"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Generate Screenshots", callback_data="generate_screenshots")],
        [InlineKeyboardButton("Generate Sample Video", callback_data="generate_sample_video")]
    ])

    message.reply_text("**Choose a function:**", reply_markup=keyboard)

@app.on_callback_query(filters.regex("generate_screenshots"))
def generate_screenshots_callback(client, callback_query):
    user_id = callback_query.from_user.id
    user_states[user_id] = "awaiting_screenshot_count"
    callback_query.message.edit_text("**How many screenshots do you want (Max: 15)?**")

@app.on_callback_query(filters.regex("generate_sample_video"))
def generate_sample_video_callback(client, callback_query):
    user_id = callback_query.from_user.id
    video_file_id = user_videos.get(user_id)
    if not video_file_id:
        callback_query.message.edit_text("**Error: No video found. Please send the video again.**")
        return

    callback_query.message.edit_text("**Please wait! Your sample video is being processed...**")

    # Download the video to a temporary file
    temp_file_path = app.download_media(video_file_id)
    video = VideoFileClip(temp_file_path)

    # Trim a 30-second segment (last 30 seconds of the video)
    if video.duration > 30:
        start_time = max(0, video.duration - 30)
        sample_video = video.subclip(start_time, video.duration)
    else:
        sample_video = video

    # Save the sample video to a file
    output_path = f"sample_video_{user_id}.mp4"
    sample_video.write_videofile(output_path, codec="libx264")

    # Send the sample video
    with open(output_path, "rb") as sample_file:
        callback_query.message.reply_video(sample_file, caption="**Here is your sample video!**")

    # Cleanup
    video.close()
    os.remove(temp_file_path)
    os.remove(output_path)

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

                # Download the video to a temporary file
                temp_file_path = app.download_media(video_file_id)
                video = VideoFileClip(temp_file_path)

                # Generate screenshots
                duration = video.duration
                interval = duration / screenshot_count
                screenshots = []

                for i in range(screenshot_count):
                    frame_time = i * interval
                    frame = video.get_frame(frame_time)

                    # Convert frame to image
                    img = Image.fromarray(frame)
                    draw = ImageDraw.Draw(img)

                    # Add watermark
                    watermark_text = "TCP Bots"
                    font = ImageFont.load_default()
                    bbox = draw.textbbox((0, 0), watermark_text, font=font)
                    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    x = img.width - text_width - 10
                    y = img.height - text_height - 10
                    draw.text((x, y), watermark_text, fill="white", font=font)

                    # Save screenshot to in-memory bytes
                    img_bytes = BytesIO()
                    img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)
                    screenshots.append(img_bytes)

                # Send all screenshots as a single message
                message.reply_media_group([InputMediaPhoto(screenshot) for screenshot in screenshots])

                # Log the request
                app.send_message(LOG_CHANNEL_ID, f"**Screenshots generated for user {user_id}.**")

                message.reply_text(
                    f"**Thank you for using the bot!**\nContact: [tcp_bots](https://t.me/{UPDATES_CHANNEL})",
                    disable_web_page_preview=True
                )

                # Cleanup
                video.close()
                os.remove(temp_file_path)

                # Clear user state and video
                user_states.pop(user_id, None)
                user_videos.pop(user_id, None)
        except ValueError:
            message.reply_text("**Invalid input. Please enter a valid number.**")

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
def stats_command(client, message):
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent

    message.reply_text(
        f"**VPS Stats:**\n\nCPU Usage: {cpu}%\nMemory Usage: {memory}%\nDisk Usage: {disk}%"
    )

@app.on_message(filters.command("users") & filters.user(OWNER_ID))
def users_command(client, message):
    total_users = get_task_count()
    message.reply_text(f"**Total Users:** {total_users}")

if __name__ == "__main__":
    print("Bot is running...")
    app.run()
