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

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
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

def save_stories():
    with open("stories.json", "w") as f:
        json.dump(stories, f)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\ud83d\udcd6 Welcome to the Story Bot!\nUse /stories to see stories or /help for all commands."
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
        "/deleteepisode <story_index> <episode_index> - Delete an episode (admin only)"
    )

# /stories
async def stories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("\u274c No stories added yet.")
        return

    keyboard = [[InlineKeyboardButton(f"{story['title']} ({story['category']})", callback_data=f"read_{i}")] for i, story in enumerate(stories)]
    await update.message.reply_text("\ud83d\udcda Choose a story:", reply_markup=InlineKeyboardMarkup(keyboard))

# /category <name>
async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("\u26a0 Usage: /category <category name>")
        return

    category = " ".join(context.args).strip().lower()
    matching = [(i, story) for i, story in enumerate(stories) if story.get("category", "").lower() == category]

    if not matching:
        await update.message.reply_text("\u274c No stories in that category.")
        return

    keyboard = [[InlineKeyboardButton(story[1]["title"], callback_data=f"read_{story[0]}")] for story in matching]
    await update.message.reply_text(f"\ud83d\udcda Stories in '{category.title()}':", reply_markup=InlineKeyboardMarkup(keyboard))

# /categories
async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_cats = {story.get("category", "Uncategorized").title() for story in stories}
    cats = "\n".join(f"\u2022 {cat}" for cat in sorted(all_cats))
    await update.message.reply_text(f"\ud83d\udcc2 Available Categories:\n{cats}")

# /continue
async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("\udc6d You haven't started a story yet. Use /stories.")
        return
    await send_episode(update.message.chat_id, user_id, context)

# /myprogress
async def myprogress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("\udc6d You haven't started reading yet.")
        return
    story = stories[prog["story"]]
    episode = prog["episode"] + 1
    await update.message.reply_text(f"\ud83d\udcd6 You're on '{story['title']}' - Episode {episode}")

# /reactions
async def reactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not reactions:
        await update.message.reply_text("\udc6d No reactions yet.")
        return

    lines = []
    for key, counts in reactions.items():
        story_idx, ep_idx = map(int, key.split("_"))
        title = stories[story_idx]["title"]
        heart = counts.get("love", 0)
        fire = counts.get("fire", 0)
        lines.append(f"\ud83d\udcd6 {title} (Ep {ep_idx + 1}): \u2764 {heart} \ud83d\udd25 {fire}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# /read <number>
async def read_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        index = int(context.args[0]) - 1
        if index < 0 or index >= len(stories):
            raise ValueError
        user_id = str(update.effective_user.id)
        user_progress[user_id] = {
            "story": index,
            "episode": 0,
            "count": 0,
            "date": datetime.date.today().isoformat()
        }
        save_user_progress()
        await send_episode(update.message.chat_id, user_id, context)
    except:
        await update.message.reply_text("\u26a0 Usage: /read <story number>")

# Delete episode command
async def delete_episode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("\u274c You're not allowed to delete episodes.")
        return

    try:
        story_idx = int(context.args[0])
        episode_idx = int(context.args[1])
        
        if 0 <= story_idx < len(stories):
            if 0 <= episode_idx < len(stories[story_idx]["episodes"]):
                deleted = stories[story_idx]["episodes"].pop(episode_idx)
                save_stories()
                await update.message.reply_text(f"\u2705 Deleted episode {episode_idx + 1} from '{stories[story_idx]['title']}'.")
            else:
                raise ValueError("Invalid episode index")
        else:
            raise ValueError("Invalid story index")
    except:
        await update.message.reply_text("\u26a0 Usage: /deleteepisode <story_index> <episode_index>")

# Button handler and episode sender skipped here for brevity
# You should copy your previous button_handler and send_episode functions here

# Unknown message
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\u274c Please use a valid command like /start or /stories.")

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
    app.add_handler(CommandHandler("deleteepisode", delete_episode_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    print("\ud83e\udd16 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

