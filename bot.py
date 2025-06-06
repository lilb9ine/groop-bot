import json
import datetime
import re
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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

# Load data

def load_json(filename, default):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

stories = load_json("stories.json", [])
user_progress = load_json("user_progress.json", {})
bookmarks = load_json("bookmarks.json", {})
comments = load_json("comments.json", {})
reactions = load_json("reactions.json", {})
story_schedules = load_json("schedules.json", {})
read_reminders = load_json("reminders.json", {})
achievements = load_json("achievements.json", {})

# Save functions

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

def save_stories(): save_json("stories.json", stories)
def save_user_progress(): save_json("user_progress.json", user_progress)
def save_bookmarks(): save_json("bookmarks.json", bookmarks)
def save_comments(): save_json("comments.json", comments)
def save_reactions(): save_json("reactions.json", reactions)
def save_schedules(): save_json("schedules.json", story_schedules)
def save_reminders(): save_json("reminders.json", read_reminders)
def save_achievements(): save_json("achievements.json", achievements)

# Helper Functions

def get_story_title(index):
    try:
        return stories[int(index)]["title"]
    except:
        return "Unknown"

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Groop Stories! Use /help to see what I can do."
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/start - Welcome message\n"
        "/help - Show help\n"
        "/stories - List all stories\n"
        "/read <number> - Read a story by number\n"
        "/continue - Continue where you left off\n"
        "/myprogress - Show your current story/episode\n"
        "/categories - List all story categories\n"
        "/category <name> - Show stories in that category\n"
        "/reactions - View total reactions\n"
        "/addstory Title: ... | Category: ... | Episodes: ep1 || ep2\n"
        "/deleteepisode <story_number> <episode_number> (admin only)\n"
        "/suggest - Get a daily story suggestion\n"
        "/search <keyword> - Search stories by keyword\n"
        "/comment <text> - Comment on your current episode\n"
        "/viewcomments - View comments on current episode\n"
        "/random - Get a random story\n"
        "/leaderboard - View top readers\n"
        "/optinreminder - Enable daily read reminders\n"
        "/optoutreminder - Disable daily read reminders\n"
        "/badges - View your achievements\n"
        "/schedulecover <story_number> <yyyy-mm-dd> - Schedule a story for future\n"
    )
    await update.message.reply_text(help_text)

# /suggest
async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("No stories available.")
        return
    suggestion = random.choice(stories)
    await update.message.reply_text(
        f"📚 Try this story today:\n*{suggestion['title']}*\nCategory: {suggestion['category']}",
        parse_mode="Markdown"
    )

# /search <keyword>
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = ' '.join(context.args).lower()
    results = [f"{i+1}. {s['title']}" for i, s in enumerate(stories) if keyword in s['title'].lower()]
    if results:
        await update.message.reply_text("🔍 Search Results:\n" + '\n'.join(results))
    else:
        await update.message.reply_text("❌ No stories found with that keyword.")

# /comment <text>
async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("❗ You haven't started reading yet.")
        return
    key = f"{prog['story']}_{prog['episode']}"
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("✍️ Provide a comment.")
        return
    if key not in comments:
        comments[key] = []
    comments[key].append({"user": user_id, "text": text})
    save_comments()
    await update.message.reply_text("💬 Comment added!")

# /viewcomments
async def view_comments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("❗ You haven't started reading yet.")
        return
    key = f"{prog['story']}_{prog['episode']}"
    cmts = comments.get(key, [])
    if not cmts:
        await update.message.reply_text("📝 No comments yet.")
    else:
        text = '\n'.join([f"User {c['user'][:5]}: {c['text']}" for c in cmts])
        await update.message.reply_text("💬 Comments:\n" + text)

# /random
async def random_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("No stories available.")
        return
    idx = random.randint(0, len(stories) - 1)
    title = stories[idx]['title']
    await update.message.reply_text(f"🎲 Random Pick: {title}\nUse /read {idx+1} to start reading.")

# /leaderboard
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    counts = {}
    for uid, prog in user_progress.items():
        counts[uid] = counts.get(uid, 0) + 1
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    text = '\n'.join([f"User {u[:5]}: {c} episodes" for u, c in top])
    await update.message.reply_text("🏆 Top Readers:\n" + text)

# /optinreminder
async def opt_in_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    read_reminders[user_id] = True
    save_reminders()
    await update.message.reply_text("🔔 Daily read reminders enabled!")

# /optoutreminder
async def opt_out_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if read_reminders.pop(user_id, None):
        save_reminders()
        await update.message.reply_text("🔕 Reminders disabled.")
    else:
        await update.message.reply_text("You weren't subscribed to reminders.")

# /badges
async def view_badges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_achievements = achievements.get(user_id, [])
    if not user_achievements:
        await update.message.reply_text("🏅 You haven't unlocked any badges yet.")
    else:
        await update.message.reply_text("🏅 Your Badges:\n" + '\n'.join(user_achievements))

# /schedulecover
async def schedule_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admins only.")
        return
    try:
        story_num = int(context.args[0]) - 1
        release_date = context.args[1]
        datetime.datetime.strptime(release_date, "%Y-%m-%d")
        story_schedules[str(story_num)] = release_date
        save_schedules()
        await update.message.reply_text("📅 Story scheduled!")
    except:
        await update.message.reply_text("Usage: /schedulecover <story_number> <yyyy-mm-dd>")

# Register handlers
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("suggest", suggest))
app.add_handler(CommandHandler("search", search))
app.add_handler(CommandHandler("comment", comment))
app.add_handler(CommandHandler("viewcomments", view_comments))
app.add_handler(CommandHandler("random", random_story))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("optinreminder", opt_in_reminder))
app.add_handler(CommandHandler("optoutreminder", opt_out_reminder))
app.add_handler(CommandHandler("badges", view_badges))
app.add_handler(CommandHandler("schedulecover", schedule_story))
# Add other command handlers as needed

# Run the bot
app.run_polling()
