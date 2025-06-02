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

BOT_TOKEN = "7589267392:AAFSu-tjVlJ7u2Zj8bpkITKM3WM3aa5nJ_s"
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
        "/addstory Title: ... | Category: ... | Episodes: ep1 || ep2 (admin only)"
    )

# /stories
async def stories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("❌ No stories added yet.")
        return

    keyboard = [[InlineKeyboardButton(f"{story['title']} ({story['category']})", callback_data=f"read_{i}")] for i, story in enumerate(stories)]
    await update.message.reply_text("📚 Choose a story:", reply_markup=InlineKeyboardMarkup(keyboard))

# /category <name>
async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠ Usage: /category <category name>")
        return

    category = " ".join(context.args).strip().lower()
    matching = [(i, story) for i, story in enumerate(stories) if story.get("category", "").lower() == category]

    if not matching:
        await update.message.reply_text("❌ No stories in that category.")
        return

    keyboard = [[InlineKeyboardButton(story[1]["title"], callback_data=f"read_{story[0]}")] for story in matching]
    await update.message.reply_text(f"📚 Stories in '{category.title()}':", reply_markup=InlineKeyboardMarkup(keyboard))

# /categories
async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_cats = {story.get("category", "Uncategorized").title() for story in stories}
    cats = "\n".join(f"• {cat}" for cat in sorted(all_cats))
    await update.message.reply_text(f"📂 Available Categories:\n{cats}")

# /continue
async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("👭 You haven't started a story yet. Use /stories.")
        return
    await send_episode(update.message.chat_id, user_id, context)

# /myprogress
async def myprogress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("👭 You haven't started reading yet.")
        return
    story = stories[prog["story"]]
    episode = prog["episode"] + 1
    await update.message.reply_text(f"📖 You're on '{story['title']}' - Episode {episode}")

# /reactions
async def reactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not reactions:
        await update.message.reply_text("👭 No reactions yet.")
        return

    lines = []
    for key, counts in reactions.items():
        story_idx, ep_idx = map(int, key.split("_"))
        title = stories[story_idx]["title"]
        heart = counts.get("love", 0)
        fire = counts.get("fire", 0)
        lines.append(f"📖 {title} (Ep {ep_idx + 1}): ❤ {heart} 🔥 {fire}")

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
        await update.message.reply_text("⚠ Usage: /read <story number>")

# Handle all button presses
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data.startswith("read_"):
        story_index = int(data.split("_")[1])
        story = stories[story_index]
        buttons = [
            [InlineKeyboardButton(f"Episode {i+1}", callback_data=f"episode_{story_index}_{i}")]
            for i in range(len(story["episodes"]))
        ]
        await query.message.reply_text(
            f"📖 {story['title']}\nChoose an episode:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("episode_"):
        _, story_idx, ep_idx = data.split("_")
        story_idx = int(story_idx)
        ep_idx = int(ep_idx)

        user_progress[user_id] = {
            "story": story_idx,
            "episode": ep_idx,
            "count": 0,
            "date": datetime.date.today().isoformat()
        }
        save_user_progress()
        await send_episode(query.message.chat_id, user_id, context)

    elif data == "next":
        prog = user_progress.get(user_id)
        if not prog:
            await query.message.reply_text("❗ Use /stories to start reading.")
            return

        today = datetime.date.today().isoformat()
        if prog["date"] != today:
            prog["count"] = 0
            prog["date"] = today

        if prog["count"] >= DAILY_LIMIT:
            await query.message.reply_text("⛔ You've reached your daily limit. Come back tomorrow!")
            return

        prog["episode"] += 1
        prog["count"] += 1
        save_user_progress()
        await send_episode(query.message.chat_id, user_id, context)

    elif data.startswith("react_"):
        try:
            _, story_idx, ep_idx, reaction = data.split("_")
            key = f"{story_idx}_{ep_idx}"

            if key not in reactions:
                reactions[key] = {"love": 0, "fire": 0}

            if reaction not in reactions[key]:
                reactions[key][reaction] = 0

            reactions[key][reaction] += 1
            save_reactions()
            await query.message.reply_text("✅ Thanks for reacting!")
        except Exception as e:
            await query.message.reply_text("⚠️ Failed to process reaction.")

# Send current episode with reactions
async def send_episode(chat_id, user_id, context):
    prog = user_progress[user_id]
    story = stories[prog["story"]]
    episodes = story["episodes"]
    ep_idx = prog["episode"]

    if ep_idx < len(episodes):
        text = f"📖 {story['title']}\n\n{episodes[ep_idx]}"
        buttons = [
            [InlineKeyboardButton("➡ Next Episode", callback_data="next")],
            [
                InlineKeyboardButton("❤ Love it", callback_data=f"react_{prog['story']}_{ep_idx}_love"),
                InlineKeyboardButton("🔥 So intense", callback_data=f"react_{prog['story']}_{ep_idx}_fire")
            ]
        ]
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await context.bot.send_message(chat_id=chat_id, text="✅ You've reached the end of the story!")

# /addstory
async def addstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You're not allowed to add stories.")
        return

    try:
        message = update.message.text
        parts = message.split("Title:")[1].split("|")
        title = parts[0].strip()
        category = ""
        episodes = []

        for part in parts[1:]:
            if "Category:" in part:
                category = part.split("Category:")[1].strip()
            elif "Episodes:" in part:
                raw_episodes = part.split("Episodes:")[1]
                episodes = [ep.strip() for ep in raw_episodes.split("||")]

        if not title or not episodes:
            raise ValueError

        stories.append({
            "title": title,
            "category": category,
            "episodes": episodes
        })

        with open("stories.json", "w") as f:
            json.dump(stories, f)

        await update.message.reply_text(f"✅ Story '{title}' added with {len(episodes)} episodes.")
    except:
        await update.message.reply_text("⚠ Format: /addstory Title: X | Category: Y | Episodes: ep1 || ep2")

# 🆕 Catch non-command messages
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Please use a valid command like /start or /stories.")

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
    app.add_handler(CallbackQueryHandler(button_handler))

    # 🆕 Catch random messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
