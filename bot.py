import json
import datetime
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
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

# Load data helpers
def load_json(filename, default):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

stories = load_json("stories.json", [])
user_progress = load_json("user_progress.json", {})
reactions = load_json("reactions.json", {})
bookmarks = load_json("bookmarks.json", {})
search_index = {}  # Optional: For search caching
leaderboard = load_json("leaderboard.json", {})
rewards = load_json("rewards.json", {})

# Save functions
def save_stories():
    save_json("stories.json", stories)

def save_user_progress():
    save_json("user_progress.json", user_progress)

def save_reactions():
    save_json("reactions.json", reactions)

def save_bookmarks():
    save_json("bookmarks.json", bookmarks)

def save_leaderboard():
    save_json("leaderboard.json", leaderboard)

def save_rewards():
    save_json("rewards.json", rewards)

# Helper for today's date string
def today_str():
    return datetime.date.today().isoformat()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Welcome to the Story Bot!\nUse /stories to browse stories or /help for commands."
    )

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Available Commands:\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/stories - List all stories\n"
        "/read <number> - Read a story by number\n"
        "/continue - Continue reading your last story\n"
        "/myprogress - Show your current reading progress\n"
        "/categories - List story categories\n"
        "/category <name> - Stories in a category\n"
        "/reactions - Show reactions stats\n"
        "/search <keyword> - Search stories\n"
        "/suggest - Suggest a story to read today\n"
        "/random - Read a random story\n"
        "/bookmarks - Show your bookmarked episodes\n"
        "/leaderboard - Top readers leaderboard\n"
        "/rewards - Your achievements\n"
        "\nAdmin Commands:\n"
        "/addstory Title: ... | Category: ... | Episodes: ep1 || ep2\n"
        "/deleteepisode <story_number> <episode_number>\n"
        "/editstory <story_number> <episode_number> <new_text>"
    )

# /stories command
async def stories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("❌ No stories available yet.")
        return
    keyboard = [[InlineKeyboardButton(f"{i+1}. {story['title']} ({story.get('category', 'Uncategorized')})", callback_data=f"read_{i}")] for i, story in enumerate(stories)]
    await update.message.reply_text("📚 Choose a story:", reply_markup=InlineKeyboardMarkup(keyboard))

# /category command
async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠ Usage: /category <category_name>")
        return
    category = " ".join(context.args).strip().lower()
    matching = [(i, s) for i, s in enumerate(stories) if s.get("category", "").lower() == category]
    if not matching:
        await update.message.reply_text(f"❌ No stories found in category '{category}'.")
        return
    keyboard = [[InlineKeyboardButton(f"{i+1}. {story['title']}", callback_data=f"read_{i}")] for i, story in matching]
    await update.message.reply_text(f"📂 Stories in '{category.title()}':", reply_markup=InlineKeyboardMarkup(keyboard))

# /categories command
async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = {s.get("category", "Uncategorized").title() for s in stories}
    if not categories:
        await update.message.reply_text("❌ No categories found.")
        return
    text = "📂 Available Categories:\n" + "\n".join(f"• {cat}" for cat in sorted(categories))
    await update.message.reply_text(text)

# /read command
async def read_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("⚠ Usage: /read <story_number>")
        return
    index = int(context.args[0]) - 1
    if index < 0 or index >= len(stories):
        await update.message.reply_text("❌ Invalid story number.")
        return
    user_id = str(update.effective_user.id)
    user_progress[user_id] = {
        "story": index,
        "episode": 0,
        "count": 0,
        "date": today_str()
    }
    save_user_progress()
    await send_episode(update.message.chat_id, user_id, context)

# /continue command
async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("👭 You haven't started reading any story yet. Use /stories to begin.")
        return
    await send_episode(update.message.chat_id, user_id, context)

# /myprogress command
async def myprogress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    prog = user_progress.get(user_id)
    if not prog:
        await update.message.reply_text("👭 You haven't started reading any story yet.")
        return
    story = stories[prog["story"]]
    episode_num = prog["episode"] + 1
    await update.message.reply_text(f"📖 You're on '{story['title']}' - Episode {episode_num}")

# /reactions command
async def reactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not reactions:
        await update.message.reply_text("👭 No reactions recorded yet.")
        return
    lines = []
    for key, counts in reactions.items():
        story_idx, ep_idx = map(int, key.split("_"))
        title = stories[story_idx]["title"]
        love_count = counts.get("love", 0)
        fire_count = counts.get("fire", 0)
        lines.append(f"📖 {title} (Ep {ep_idx + 1}): ❤ {love_count} 🔥 {fire_count}")
    await update.message.reply_text("\n".join(lines))

# /addstory command (admin only)
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
                raw_eps = part.split("Episodes:")[1]
                episodes = [ep.strip() for ep in raw_eps.split("||") if ep.strip()]
        if not title or not episodes:
            raise ValueError
        stories.append({"title": title, "category": category, "episodes": episodes})
        save_stories()
        await update.message.reply_text(f"✅ Story '{title}' added with {len(episodes)} episodes.")
    except Exception:
        await update.message.reply_text("⚠ Usage: /addstory Title: X | Category: Y | Episodes: ep1 || ep2")

# /deleteepisode command (admin only)
async def delete_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to delete episodes.")
        return
    if len(context.args) < 2 or not all(arg.isdigit() for arg in context.args[:2]):
        await update.message.reply_text("⚠ Usage: /deleteepisode <story_number> <episode_number>")
        return
    story_idx = int(context.args[0]) - 1
    ep_idx = int(context.args[1]) - 1
    if story_idx < 0 or story_idx >= len(stories):
        await update.message.reply_text("❌ Invalid story number.")
        return
    if ep_idx < 0 or ep_idx >= len(stories[story_idx]["episodes"]):
        await update.message.reply_text("❌ Invalid episode number.")
        return
    del stories[story_idx]["episodes"][ep_idx]
    save_stories()
    await update.message.reply_text(f"✅ Episode {ep_idx+1} deleted from '{stories[story_idx]['title']}'.")

# /editstory command (admin only)
async def editstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to edit stories.")
        return
    if len(context.args) < 3 or not (context.args[0].isdigit() and context.args[1].isdigit()):
        await update.message.reply_text("⚠ Usage: /editstory <story_number> <episode_number> <new_text>")
        return
    story_idx = int(context.args[0]) - 1
    ep_idx = int(context.args[1]) - 1
    new_text = " ".join(context.args[2:])
    if story_idx < 0 or story_idx >= len(stories):
        await update.message.reply_text("❌ Invalid story number.")
        return
    if ep_idx < 0 or ep_idx >= len(stories[story_idx]["episodes"]):
        await update.message.reply_text("❌ Invalid episode number.")
        return
    stories[story_idx]["episodes"][ep_idx] = new_text
    save_stories()
    await update.message.reply_text(f"✅ Episode {ep_idx+1} of '{stories[story_idx]['title']}' updated.")

# /search command
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠ Usage: /search <keyword>")
        return
    keyword = " ".join(context.args).lower()
    results = []
    for i, story in enumerate(stories):
        if keyword in story["title"].lower() or any(keyword in ep.lower() for ep in story["episodes"]):
            results.append((i, story))
    if not results:
        await update.message.reply_text(f"❌ No stories found matching '{keyword}'.")
        return
    keyboard = [[InlineKeyboardButton(f"{i+1}. {story['title']}", callback_data=f"read_{i}")] for i, story in results]
    await update.message.reply_text(f"🔎 Search results for '{keyword}':", reply_markup=InlineKeyboardMarkup(keyboard))

# /suggest command - Suggest a random story
async def suggest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("❌ No stories available.")
        return
    story = random.choice(stories)
    idx = stories.index(story)
    keyboard = [[InlineKeyboardButton(f"Read '{story['title']}'", callback_data=f"read_{idx}")]]
    await update.message.reply_text(f"📖 Today's story suggestion:\n{story['title']}", reply_markup=InlineKeyboardMarkup(keyboard))

# /random command - Read a random story immediately
async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("❌ No stories available.")
        return
    user_id = str(update.effective_user.id)
    idx = random.randint(0, len(stories) - 1)
    user_progress[user_id] = {"story": idx, "episode": 0, "count": 0, "date": today_str()}
    save_user_progress()
    await send_episode(update.message.chat_id, user_id, context)

# /bookmarks command - Show user's bookmarks
async def bookmarks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_bm = bookmarks.get(user_id, [])
    if not user_bm:
        await update.message.reply_text("📑 You have no bookmarks yet.")
        return
    lines = []
    for (story_idx, ep_idx) in user_bm:
        story = stories[story_idx]
        lines.append(f"{story['title']} - Episode {ep_idx + 1}")
    await update.message.reply_text("📑 Your bookmarks:\n" + "\n".join(lines))

# /leaderboard command - Show top readers
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not leaderboard:
        await update.message.reply_text("👭 No reading data yet.")
        return
    sorted_lb = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = []
    for user, count in sorted_lb:
        lines.append(f"👤 User {user}: {count} episodes read")
    await update.message.reply_text("🏆 Top Readers:\n" + "\n".join(lines))

# /rewards command - Show user's achievements
async def rewards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_rewards = rewards.get(user_id, [])
    if not user_rewards:
        await update.message.reply_text("🎖️ You have no rewards yet.")
        return
    await update.message.reply_text("🎖️ Your Achievements:\n" + "\n".join(user_rewards))

# Helper to send episode text with reactions and bookmark buttons
async def send_episode(chat_id, user_id, context):
    prog = user_progress.get(user_id)
    if not prog:
        await context.bot.send_message(chat_id=chat_id, text="👭 You haven't started any story yet.")
        return
    story_idx = prog["story"]
    ep_idx = prog["episode"]
    story = stories[story_idx]

    # Check daily limit
    if prog.get("date") != today_str():
        prog["count"] = 0
        prog["date"] = today_str()
    if prog["count"] >= DAILY_LIMIT:
        await context.bot.send_message(chat_id=chat_id, text="⚠ You have reached your daily reading limit.")
        return

    episodes = story["episodes"]
    if ep_idx >= len(episodes):
        await context.bot.send_message(chat_id=chat_id, text="✅ You've finished this story!")
        return

    text = f"📖 *{story['title']}* - Episode {ep_idx + 1}\n\n{episodes[ep_idx]}"
    prog["count"] += 1
    save_user_progress()

    # Update leaderboard
    leaderboard[user_id] = leaderboard.get(user_id, 0) + 1
    save_leaderboard()

    # Update rewards (simple example)
    if leaderboard[user_id] == 10 and "Read 10 episodes" not in rewards.get(user_id, []):
        rewards.setdefault(user_id, []).append("🏅 Read 10 episodes")
        save_rewards()

    # Prepare reaction and bookmark buttons
    key = f"{story_idx}_{ep_idx}"
    react_counts = reactions.get(key, {"love": 0, "fire": 0})

    keyboard = [
        [
            InlineKeyboardButton(f"❤️ {react_counts.get('love', 0)}", callback_data=f"react_{key}_love"),
            InlineKeyboardButton(f"🔥 {react_counts.get('fire', 0)}", callback_data=f"react_{key}_fire"),
        ],
        [
            InlineKeyboardButton("Bookmark 📑", callback_data=f"bookmark_{key}"),
            InlineKeyboardButton("Next ▶️", callback_data="next_episode")
        ],
    ]
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# Callback handler for reactions, bookmarks, and next episode
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data

    if data.startswith("react_"):
        _, key, react = data.split("_")
        counts = reactions.setdefault(key, {"love": 0, "fire": 0})
        counts[react] = counts.get(react, 0) + 1
        save_reactions()
        await query.answer(f"Thanks for your reaction {react}!")
        # Optionally update button counts
        await query.edit_message_reply_markup(reply_markup=update_reaction_markup(key))
        return

    if data.startswith("bookmark_"):
        _, key = data.split("_")
        story_idx, ep_idx = map(int, key.split("_"))
        user_bm = bookmarks.setdefault(user_id, [])
        if (story_idx, ep_idx) not in user_bm:
            user_bm.append((story_idx, ep_idx))
            save_bookmarks()
            await query.answer("📑 Bookmarked!")
        else:
            await query.answer("📑 Already bookmarked!")
        return

    if data == "next_episode":
        prog = user_progress.get(user_id)
        if not prog:
            await query.answer("You haven't started any story.")
            return
        prog["episode"] += 1
        save_user_progress()
        await query.answer("▶️ Loading next episode...")
        await send_episode(query.message.chat_id, user_id, context)
        # Delete old message to keep chat clean
        await query.message.delete()
        return

    if data.startswith("read_"):
        story_idx = int(data.split("_")[1])
        user_progress[user_id] = {"story": story_idx, "episode": 0, "count": 0, "date": today_str()}
        save_user_progress()
        await query.answer()
        await send_episode(query.message.chat_id, user_id, context)
        await query.message.delete()
        return

def update_reaction_markup(key):
    counts = reactions.get(key, {"love": 0, "fire": 0})
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"❤️ {counts.get('love', 0)}", callback_data=f"react_{key}_love"),
            InlineKeyboardButton(f"🔥 {counts.get('fire', 0)}", callback_data=f"react_{key}_fire"),
        ],
        [
            InlineKeyboardButton("Bookmark 📑", callback_data=f"bookmark_{key}"),
            InlineKeyboardButton("Next ▶️", callback_data="next_episode")
        ],
    ])

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stories", stories_command))
    app.add_handler(CommandHandler("read", read_command))
    app.add_handler(CommandHandler("continue", continue_command))
    app.add_handler(CommandHandler("myprogress", myprogress))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(CommandHandler("category", category_command))
    app.add_handler(CommandHandler("reactions", reactions_command))
    app.add_handler(CommandHandler("addstory", addstory))
    app.add_handler(CommandHandler("deleteepisode", delete_episode))
    app.add_handler(CommandHandler("editstory", editstory))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("suggest", suggest_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("bookmarks", bookmarks_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("rewards", rewards_command))

    # Callback query handler for buttons
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Set bot commands for menu with shortcodes
    commands = [
        BotCommand("start", "🏠 Start"),
        BotCommand("help", "❓ Help"),
        BotCommand("stories", "📚 List stories |stories"),
        BotCommand("read", "📖 Read a story |read"),
        BotCommand("continue", "▶️ Continue reading |continue"),
        BotCommand("myprogress", "📊 My progress |myprogress"),
        BotCommand("categories", "📂 List categories |categories"),
        BotCommand("category", "📁 Show category stories |category"),
        BotCommand("reactions", "❤️🔥 Show reactions |reactions"),
        BotCommand("search", "🔍 Search stories |search"),
        BotCommand("suggest", "💡 Suggest a story |suggest"),
        BotCommand("random", "🎲 Random story |random"),
        BotCommand("bookmarks", "📑 My bookmarks |bookmarks"),
        BotCommand("leaderboard", "🏆 Top readers |leaderboard"),
        BotCommand("rewards", "🎖️ Achievements |rewards"),
        BotCommand("addstory", "➕ Add story (admin) |addstory"),
        BotCommand("deleteepisode", "🗑️ Delete episode (admin) |deleteepisode"),
        BotCommand("editstory", "✏️ Edit episode (admin) |editstory"),
    ]
    await app.bot.set_my_commands(commands)

    print("Bot started...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
