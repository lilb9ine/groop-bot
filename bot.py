import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

BOT_TOKEN = "7788167620:AAFFHyGKTp4PJL0_cav_jnesdm2mOlvSGpc"
ADMIN_ID = 6027059388
DAILY_LIMIT = 10

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

# Load reactions
try:
    with open("reactions.json", "r") as f:
        reactions = json.load(f)
except FileNotFoundError:
    reactions = {}

def save_user_progress():
    with open("user_progress.json", "w") as f:
        json.dump(user_progress, f)

def save_reactions():
    with open("reactions.json", "w") as f:
        json.dump(reactions, f)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Welcome to the Story Bot!\nUse /stories to see stories or /help for all commands."
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Welcome message\n"
        "/help - Show help\n"
        "/stories - List all stories\n"
        "/read <number> - Read a story by number\n"
        "/continue - Continue where you left off\n"
        "/myprogress - Show your current story/episode\n"
        "/categories - List all story categories\n"
        "/category <name> - Show stories in that category\n"
        "/reactions - View total reactions\n"
        "/addstory Title: ... | Category: ... | Episodes: ep1 || ep2 (admin only)\n"
        "/deleteepisode <story_number> <episode_number> (admin only)"
    )

# ... [NO CHANGES to other handlers above] ...

# /deleteepisode <story_number> <episode_number>
async def delete_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You're not allowed to delete episodes.")
        return

    try:
        story_idx = int(context.args[0]) - 1
        ep_idx = int(context.args[1]) - 1

        if story_idx < 0 or story_idx >= len(stories):
            raise ValueError("Invalid story number")

        story = stories[story_idx]

        if ep_idx < 0 or ep_idx >= len(story["episodes"]):
            raise ValueError("Invalid episode number")

        deleted = story["episodes"].pop(ep_idx)

        with open("stories.json", "w") as f:
            json.dump(stories, f)

        await update.message.reply_text(f"✅ Deleted episode {ep_idx + 1} from '{story['title']}'.")
    except Exception as e:
        await update.message.reply_text("⚠ Usage: /deleteepisode <story_number> <episode_number>")

# Start bot

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stories", stories_command))
    app.add_handler(CommandHandler("read", read_command))
    app.add_handler(CommandHandler("continue", continue_command))
    app.add_handler(CommandHandler("myprogress", myprogress))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(CommandHandler("category", category_command))
    app.add_handler(CommandHandler("addstory", addstory))
    app.add_handler(CommandHandler("reactions", reactions_command))
    app.add_handler(CommandHandler("deleteepisode", delete_episode))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
