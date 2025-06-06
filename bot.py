import json
import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
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

# Load reactions
try:
    with open("reactions.json", "r") as f:
        reactions = json.load(f)
except FileNotFoundError:
    reactions = {}

def save_stories():
    with open("stories.json", "w") as f:
        json.dump(stories, f, indent=2)

def save_user_progress():
    with open("user_progress.json", "w") as f:
        json.dump(user_progress, f, indent=2)

def save_reactions():
    with open("reactions.json", "w") as f:
        json.dump(reactions, f, indent=2)

# Command Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Welcome to the Story Bot!\nUse /stories to see stories or /help for all commands."
    )

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

async def stories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("❌ No stories added yet.")
        return
    keyboard = [[InlineKeyboardButton(f"{story['title']} ({story.get('category','Uncategorized')})", callback_data=f"read_{i}")]
                for i, story in enumerate(stories)]
    await update.message.reply_text("📚 Choose a story:", reply_markup=InlineKeyboardMarkup(keyboard))

async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠ Usage: /category <category name>")
        return
    category = " ".join(context.args).strip().lower()
    matching = [(i, story) for i, story in enumerate(stories) if story.get("category", "").lower() == category]
    if not matching:
        await update.message.reply_text(f"❌ No stories found in category '{category}'.")
        return
    keyboard = [[InlineKeyboardButton(story[1]["title"], callback_data=f"read_{story[0]}")] for story in matching]
    await update.message.reply_text(f"📚 Stories in '{category.title()}':", reply_markup=InlineKeyboardMarkup(keyboard))

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_cats = {story.get("category", "Uncategorized").title() for story in stories}
    if not all_cats:
        await update.message.reply_text("❌ No categories found.")
        return
    cats = "\n".join(f"• {cat}" for cat in sorted(all_cats))
    await update.message.reply_text(f"📂 Available Categories:\n{cats}")

async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("👭 You haven't started a story yet. Use /stories.")
        return
    await send_episode(update.message.chat_id, user_id, context)

async def myprogress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("👭 You haven't started reading any story yet.")
        return
    story = stories[prog["story"]]
    episode_num = prog["episode"] + 1
    await update.message.reply_text(f"📖 You're on '{story['title']}' - Episode {episode_num}")

async def reactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not reactions:
        await update.message.reply_text("👭 No reactions recorded yet.")
        return
    lines = []
    for key, counts in reactions.items():
        story_idx, ep_idx = map(int, key.split("_"))
        title = stories[story_idx]["title"]
        heart = counts.get("love", 0)
        fire = counts.get("fire", 0)
        lines.append(f"📖 {title} (Ep {ep_idx + 1}): ❤️ {heart} 🔥 {fire}")
    await update.message.reply_text("\n".join(lines))

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
            "date": datetime.date.today().isoformat(),
        }
        save_user_progress()
        await send_episode(update.message.chat_id, user_id, context)
    except Exception:
        await update.message.reply_text("⚠ Usage: /read <story number>")

async def addstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to add stories.")
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
                episodes = [ep.strip() for ep in raw_episodes.split("||") if ep.strip()]

        if not title or not episodes:
            raise ValueError

        stories.append({
            "title": title,
            "category": category,
            "episodes": episodes,
        })
        save_stories()
        await update.message.reply_text(f"✅ Story '{title}' added with {len(episodes)} episodes.")
    except Exception:
        await update.message.reply_text(
            "⚠ Format: /addstory Title: <title> | Category: <category> | Episodes: ep1 || ep2 || ep3"
        )

async def delete_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to delete episodes.")
        return
    try:
        story_idx = int(context.args[0]) - 1
        ep_idx = int(context.args[1]) - 1
        if story_idx < 0 or ep_idx < 0 or story_idx >= len(stories):
            raise ValueError
        if ep_idx >= len(stories[story_idx]["episodes"]):
            await update.message.reply_text("❌ Invalid episode number.")
            return
        del stories[story_idx]["episodes"][ep_idx]
        save_stories()
        await update.message.reply_text(
            f"✅ Episode {ep_idx + 1} deleted from story '{stories[story_idx]['title']}'."
        )
    except Exception:
        await update.message.reply_text("⚠ Usage: /deleteepisode <story_number> <episode_number>")

# CallbackQueryHandler for inline buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data.startswith("read_"):
        story_index = int(data.split("_")[1])
        story = stories[story_index]
        buttons = [
            [InlineKeyboardButton(f"Episode {i + 1}", callback_data=f"episode_{story_index}_{i}")]
            for i in range(len(story["episodes"]))
        ]
        await query.message.reply_text(
            f"📖 {story['title']}\nChoose an episode:", reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("episode_"):
        _, story_idx, ep_idx = data.split("_")
        story_idx = int(story_idx)
        ep_idx = int(ep_idx)

        user_progress[user_id] = {
            "story": story_idx,
            "episode": ep_idx,
            "count": 0,
            "date": datetime.date.today().isoformat(),
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
            await query.message.reply_text("❌ Daily reading limit reached (30 episodes). Come back tomorrow.")
            return

        story_idx = prog["story"]
        ep_idx = prog["episode"] + 1

        if ep_idx >= len(stories[story_idx]["episodes"]):
            await query.message.reply_text("🎉 You've finished this story!")
            return

        prog["episode"] = ep_idx
        prog["count"] += 1
        save_user_progress()
        await send_episode(query.message.chat_id, user_id, context)

    elif data.startswith("react_"):
        _, story_idx, ep_idx, reaction = data.split("_")
        key = f"{story_idx}_{ep_idx}"
        if key not in reactions:
            reactions[key] = {"love": 0, "fire": 0}
        reactions[key][reaction] += 1
        save_reactions()
        await query.answer("Reaction recorded!")

async def send_episode(chat_id, user_id, context: ContextTypes.DEFAULT_TYPE):
    prog = user_progress.get(user_id)
    if not prog:
        await context.bot.send_message(chat_id, "👭 You have no story in progress. Use /stories.")
        return

    story_idx = prog["story"]
    ep_idx = prog["episode"]
    story = stories[story_idx]
    episodes = story["episodes"]

    if ep_idx >= len(episodes):
        await context.bot.send_message(chat_id, "🎉 You have finished all episodes!")
        return

    ep_text = episodes[ep_idx]
    text = f"📚 *{story['title']}* - Episode {ep_idx + 1}\n\n{ep_text}"

    keyboard = [
        [InlineKeyboardButton("Next ▶️", callback_data="next")],
        [
            InlineKeyboardButton("❤️", callback_data=f"react_{story_idx}_{ep_idx}_love"),
            InlineKeyboardButton("🔥", callback_data=f"react_{story_idx}_{ep_idx}_fire"),
        ],
    ]

    await context.bot.send_message(
        chat_id, text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Use /help to see available commands.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stories", stories_command))
    app.add_handler(CommandHandler("category", category_command))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(CommandHandler("continue", continue_command))
    app.add_handler(CommandHandler("myprogress", myprogress))
    app.add_handler(CommandHandler("reactions", reactions_command))
    app.add_handler(CommandHandler("read", read_command))
    app.add_handler(CommandHandler("addstory", addstory))
    app.add_handler(CommandHandler("deleteepisode", delete_episode))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    # Set command shortcuts (menu)
    await app.bot.set_my_commands([
        ("start", "Welcome message"),
        ("help", "Show help"),
        ("stories", "List all stories"),
        ("read", "Read a story by number"),
        ("continue", "Continue reading"),
        ("myprogress", "Show progress"),
        ("categories", "List all categories"),
        ("category", "Show stories in category"),
        ("reactions", "View reactions"),
        ("addstory", "Add new story (admin only)"),
        ("deleteepisode", "Delete episode (admin only)")
    ])

    print("🤖 Bot started...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "running event loop" in str(e):
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise

      
