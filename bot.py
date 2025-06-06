
import json
import datetime
import re  # for keyword search
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

BOT_TOKEN = "7589267392:AAFSu-tjVlJ7u2Zj8bpkITKM3WM3aa5nJ_s"
ADMIN_ID = 6027059388
DAILY_LIMIT = 30

# Load stories
try:
    with open("stories.json", "r") as f:
        stories = json.load(f)
except FileNotFoundError:
    stories = []

# Load user progress
try:
    with open("user_progress.json", "r") as f:
        user_progress = json.load(f)
except FileNotFoundError:
    user_progress = {}

# Load bookmarks
try:
    with open("bookmarks.json", "r") as f:
        bookmarks = json.load(f)
except FileNotFoundError:
    bookmarks = {}

def save_stories():
    with open("stories.json", "w") as f:
        json.dump(stories, f)

def save_user_progress():
    with open("user_progress.json", "w") as f:
        json.dump(user_progress, f)

def save_bookmarks():
    with open("bookmarks.json", "w") as f:
        json.dump(bookmarks, f)

# /bookmark command
async def bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("❗ You haven't started reading yet.")
        return

    key = f"{prog['story']}_{prog['episode']}"
    if user_id not in bookmarks:
        bookmarks[user_id] = []
    if key not in bookmarks[user_id]:
        bookmarks[user_id].append(key)
        save_bookmarks()
        await update.message.reply_text("🔖 Episode bookmarked!")
    else:
        await update.message.reply_text("✅ Already bookmarked.")

# /bookmarks command
async def view_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_bm = bookmarks.get(user_id, [])

    if not user_bm:
        await update.message.reply_text("📭 You have no bookmarks yet.")
        return

    lines = []
    for bm in user_bm:
        s_idx, e_idx = map(int, bm.split("_"))
        story = stories[s_idx]
        title = story["title"]
        lines.append(f"📘 {title} - Episode {e_idx + 1}")

    await update.message.reply_text("\n".join(lines))

# /addstory (admin only)
async def add_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can add stories.")
        return

    try:
        title, *episodes = update.message.text.replace("/addstory", "", 1).strip().split("::")
        story = {"title": title.strip(), "episodes": [ep.strip() for ep in episodes]}
        stories.append(story)
        save_stories()
        await update.message.reply_text(f"✅ Story '{title.strip()}' added with {len(episodes)} episodes.")
    except Exception as e:
        await update.message.reply_text("❗ Error formatting story. Use: /addstory Title::Episode1::Episode2::...")

# /readstory
async def read_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(story["title"], callback_data=f"read_{i}")]
        for i, story in enumerate(stories)
    ]
    await update.message.reply_text("📚 Choose a story:", reply_markup=InlineKeyboardMarkup(keyboard))

# Handle story selection
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = str(query.from_user.id)

    if data.startswith("read_"):
        story_idx = int(data.split("_")[1])
        user_progress[user_id] = {"story": story_idx, "episode": 0}
        save_user_progress()
        episode = stories[story_idx]["episodes"][0]
        await query.message.reply_text(f"📖 {episode}")
    elif data.startswith("next"):
        story_idx = user_progress[user_id]["story"]
        ep_idx = user_progress[user_id]["episode"] + 1
        if ep_idx < len(stories[story_idx]["episodes"]):
            user_progress[user_id]["episode"] = ep_idx
            save_user_progress()
            await query.message.reply_text(f"📖 {stories[story_idx]['episodes'][ep_idx]}")
        else:
            await query.message.reply_text("🏁 You've finished this story!")

# /continue
async def continue_reading(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    progress = user_progress.get(user_id)
    if not progress:
        await update.message.reply_text("❗ You haven't started any story.")
        return

    story = stories[progress["story"]]
    ep_idx = progress["episode"]
    await update.message.reply_text(f"📖 {story['episodes'][ep_idx]}")

# Main entry
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the Story Bot!\nUse /readstory to begin.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("readstory", read_story))
    app.add_handler(CommandHandler("continue", continue_reading))
    app.add_handler(CommandHandler("addstory", add_story))
    app.add_handler(CommandHandler("bookmark", bookmark))
    app.add_handler(CommandHandler("bookmarks", view_bookmarks))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()
