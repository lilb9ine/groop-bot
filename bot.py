import json
import datetime
import re
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

# Save functions
def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

def save_stories(): save_json("stories.json", stories)
def save_user_progress(): save_json("user_progress.json", user_progress)
def save_bookmarks(): save_json("bookmarks.json", bookmarks)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the Story Bot! Use /help to see what you can do.")

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠 Available Commands:\n\n"
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
        "/deleteepisode <story_number> <episode_number> (admin only)"
    )
    await update.message.reply_text(help_text)

# /stories
async def stories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("📭 No stories available.")
        return

    text = "\n".join([f"{i+1}. {s['title']} ({s['category']})" for i, s in enumerate(stories)])
    await update.message.reply_text(f"📚 Available Stories:\n{text}")

# /read
async def read_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /read <story_number>")
        return

    try:
        index = int(context.args[0]) - 1
        if index < 0 or index >= len(stories):
            raise IndexError
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid story number.")
        return

    user_id = str(update.effective_user.id)
    story = stories[index]
    user_progress[user_id] = {"story": index, "episode": 0, "last_read": str(datetime.date.today())}
    save_user_progress()
    await update.message.reply_text(f"📖 {story['title']}\n\n{story['episodes'][0]}")

# /continue
async def continue_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("❗ You haven't started any story yet.")
        return

    story = stories[prog['story']]
    ep = prog['episode'] + 1
    if ep >= len(story['episodes']):
        await update.message.reply_text("🏁 You've finished this story!")
        return

    user_progress[user_id]['episode'] = ep
    user_progress[user_id]['last_read'] = str(datetime.date.today())
    save_user_progress()
    await update.message.reply_text(f"📖 {story['title']}\n\n{story['episodes'][ep]}")

# /myprogress
async def myprogress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("📭 No reading progress found.")
        return
    story = stories[prog['story']]
    await update.message.reply_text(f"📘 You're reading '{story['title']}', episode {prog['episode']+1}.")

# /categories
async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = sorted(set(s['category'] for s in stories))
    await update.message.reply_text("📂 Categories:\n" + "\n".join(cats))

# /category <name>
async def category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /category <name>")
        return
    name = " ".join(context.args).lower()
    filtered = [f"{i+1}. {s['title']}" for i, s in enumerate(stories) if s['category'].lower() == name]
    if not filtered:
        await update.message.reply_text("❌ No stories found in this category.")
    else:
        await update.message.reply_text("📚 Stories in category:\n" + "\n".join(filtered))

# /bookmark
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

# /bookmarks
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
        lines.append(f"{story['title']} - Episode {e_idx + 1}")
    await update.message.reply_text("🔖 Your Bookmarks:\n" + "\n".join(lines))

# /addstory
async def addstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You're not allowed to use this command.")
        return
    text = update.message.text.replace("/addstory", "").strip()
    try:
        title = re.search(r"Title: (.*?) \|", text).group(1).strip()
        category = re.search(r"Category: (.*?) \|", text).group(1).strip()
        episodes = re.search(r"Episodes: (.*)", text).group(1).split("||")
        stories.append({"title": title, "category": category, "episodes": [ep.strip() for ep in episodes]})
        save_stories()
        await update.message.reply_text("✅ Story added.")
    except Exception as e:
        await update.message.reply_text("⚠️ Error adding story. Check your format.")

# /deleteepisode
async def deleteepisode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You're not allowed to use this command.")
        return
    try:
        s_idx = int(context.args[0]) - 1
        e_idx = int(context.args[1]) - 1
        stories[s_idx]['episodes'].pop(e_idx)
        save_stories()
        await update.message.reply_text("🗑️ Episode deleted.")
    except:
        await update.message.reply_text("⚠️ Usage: /deleteepisode <story_number> <episode_number>")

# Main
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("stories", stories_command))
app.add_handler(CommandHandler("read", read_story))
app.add_handler(CommandHandler("continue", continue_story))
app.add_handler(CommandHandler("myprogress", myprogress))
app.add_handler(CommandHandler("categories", categories))
app.add_handler(CommandHandler("category", category))
app.add_handler(CommandHandler("bookmark", bookmark))
app.add_handler(CommandHandler("bookmarks", view_bookmarks))
app.add_handler(CommandHandler("addstory", addstory))
app.add_handler(CommandHandler("deleteepisode", deleteepisode))

print("✅ Bot running...")
app.run_polling()
