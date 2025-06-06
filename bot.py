import json
import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
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

# Load bookmarks
try:
    with open("bookmarks.json", "r") as f:
        bookmarks = json.load(f)
except FileNotFoundError:
    bookmarks = {}

# Load leaderboard data (episodes read count)
try:
    with open("leaderboard.json", "r") as f:
        leaderboard = json.load(f)
except FileNotFoundError:
    leaderboard = {}

def save_stories():
    with open("stories.json", "w") as f:
        json.dump(stories, f)

def save_user_progress():
    with open("user_progress.json", "w") as f:
        json.dump(user_progress, f)

def save_reactions():
    with open("reactions.json", "w") as f:
        json.dump(reactions, f)

def save_bookmarks():
    with open("bookmarks.json", "w") as f:
        json.dump(bookmarks, f)

def save_leaderboard():
    with open("leaderboard.json", "w") as f:
        json.dump(leaderboard, f)

# Custom Reply Keyboard (menu)
menu_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("/stories"), KeyboardButton("/categories")],
        [KeyboardButton("/myprogress"), KeyboardButton("/bookmarks")],
        [KeyboardButton("/search"), KeyboardButton("/random")],
        [KeyboardButton("/help")]
    ],
    resize_keyboard=True
)

# /start - send welcome and show menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Welcome to the Story Bot!\nUse the menu below or commands like /stories.",
        reply_markup=menu_keyboard
    )

# /help - add info about new commands
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
        "/addstory Title: ... | Category: ... | Episodes: ep1 || ep2\n"
        "/deleteepisode <story_number> <episode_number> (admin only)\n"
        "/bookmarks - Show your bookmarks\n"
        "/bookmark <story_number> <episode_number> - Add a bookmark\n"
        "/removebookmark <story_number> <episode_number> - Remove a bookmark\n"
        "/search <keyword> - Search stories by title or episode\n"
        "/random - Read a random story\n"
        "/leaderboard - Top readers leaderboard\n"
        "/editstory <story_number> Title: ... | Category: ... | Episodes: ep1 || ep2 (admin only)"
    )

# Bookmarks commands

async def bookmarks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_bookmarks = bookmarks.get(user_id, [])
    if not user_bookmarks:
        await update.message.reply_text("📑 You have no bookmarks.")
        return

    text_lines = []
    for bm in user_bookmarks:
        s_idx, e_idx = bm
        if s_idx < len(stories) and e_idx < len(stories[s_idx]["episodes"]):
            title = stories[s_idx]["title"]
            text_lines.append(f"• {title} - Episode {e_idx + 1}")
    await update.message.reply_text("📑 Your bookmarks:\n" + "\n".join(text_lines))

async def add_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) < 2:
        await update.message.reply_text("⚠ Usage: /bookmark <story_number> <episode_number>")
        return

    try:
        s_idx = int(context.args[0]) - 1
        e_idx = int(context.args[1]) - 1
        if s_idx < 0 or e_idx < 0:
            raise ValueError

        if s_idx >= len(stories):
            await update.message.reply_text("❌ Invalid story number.")
            return
        if e_idx >= len(stories[s_idx]["episodes"]):
            await update.message.reply_text("❌ Invalid episode number.")
            return

        user_bookmarks = bookmarks.setdefault(user_id, [])
        if [s_idx, e_idx] in user_bookmarks:
            await update.message.reply_text("⚠ This episode is already bookmarked.")
            return

        user_bookmarks.append([s_idx, e_idx])
        save_bookmarks()
        await update.message.reply_text(f"✅ Bookmarked '{stories[s_idx]['title']}' Episode {e_idx + 1}")
    except:
        await update.message.reply_text("⚠ Usage: /bookmark <story_number> <episode_number>")

async def remove_bookmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) < 2:
        await update.message.reply_text("⚠ Usage: /removebookmark <story_number> <episode_number>")
        return

    try:
        s_idx = int(context.args[0]) - 1
        e_idx = int(context.args[1]) - 1
        user_bookmarks = bookmarks.get(user_id, [])

        if [s_idx, e_idx] not in user_bookmarks:
            await update.message.reply_text("❌ Bookmark not found.")
            return

        user_bookmarks.remove([s_idx, e_idx])
        save_bookmarks()
        await update.message.reply_text(f"✅ Removed bookmark for '{stories[s_idx]['title']}' Episode {e_idx + 1}")
    except:
        await update.message.reply_text("⚠ Usage: /removebookmark <story_number> <episode_number>")

# Search command

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠ Usage: /search <keyword>")
        return

    keyword = " ".join(context.args).lower()
    matches = []

    for i, story in enumerate(stories):
        if keyword in story["title"].lower():
            matches.append((i, story["title"]))
            continue
        for ep in story["episodes"]:
            if keyword in ep.lower():
                matches.append((i, story["title"]))
                break

    if not matches:
        await update.message.reply_text("❌ No matching stories found.")
        return

    keyboard = [[InlineKeyboardButton(f"{title}", callback_data=f"read_{i}")] for i, title in matches]
    await update.message.reply_text(f"🔍 Search results for '{keyword}':", reply_markup=InlineKeyboardMarkup(keyboard))

# Random story

import random

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not stories:
        await update.message.reply_text("❌ No stories available.")
        return
    idx = random.randint(0, len(stories) - 1)
    user_id = str(update.effective_user.id)
    user_progress[user_id] = {
        "story": idx,
        "episode": 0,
        "count": 0,
        "date": datetime.date.today().isoformat(),
    }
    save_user_progress()
    await send_episode(update.message.chat_id, user_id, context)

# Leaderboard - top users by episodes read

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not leaderboard:
        await update.message.reply_text("📊 No reading activity yet.")
        return

    sorted_leaderboard = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)[:10]
    text_lines = ["🏆 Top readers:"]
    for user_id, count in sorted_leaderboard:
        # Display username or user_id
        text_lines.append(f"• User {user_id}: {count} episodes read")
    await update.message.reply_text("\n".join(text_lines))

# Update leaderboard helper (increment episodes read count)
def update_leaderboard(user_id: str):
    leaderboard[user_id] = leaderboard.get(user_id, 0) + 1
    save_leaderboard()

# Admin: edit story command
async def editstory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to edit stories.")
        return

    try:
        message = update.message.text
        parts = message.split(" ", 1)
        if len(parts) < 2:
            raise ValueError
        args = parts[1].split("Title:")
        story_num = int(args[0].strip()) - 1
        if story_num < 0 or story_num >= len(stories):
            await update.message.reply_text("❌ Invalid story number.")
            return

        parts2 = args[1].split("|")
        title = parts2[0].strip()
        category = ""
        episodes = []

        for part in parts2[1:]:
            if "Category:" in part:
                category = part.split("Category:")[1].strip()
            elif "Episodes:" in part:
                raw_episodes = part.split("Episodes:")[1]
                episodes = [ep.strip() for ep in raw_episodes.split("||")]

        if not title or not episodes:
            await update.message.reply_text("⚠ Title and episodes cannot be empty.")
            return

        stories[story_num]["title"] = title
        stories[story_num]["category"] = category
        stories[story_num]["episodes"] = episodes
        save_stories()
        await update.message.reply_text(f"✅ Story #{story_num + 1} updated.")
    except Exception as e:
        await update.message.reply_text("⚠ Usage: /editstory <story_number> Title: ... | Category: ... | Episodes: ep1 || ep2")

# Updated send_episode to update leaderboard on episode send

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
                InlineKeyboardButton("🔥 So intense", callback_data=f"react_{prog['story']}_{ep_idx}_fire"),
            ],
            [
                InlineKeyboardButton("🔖 Bookmark", callback_data=f"bookmark_{prog['story']}_{ep_idx}")
            ],
        ]
        # Update leaderboard
        update_leaderboard(user_id)

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text="✅ You've reached the end of the story!")

# Extend button handler to handle bookmark inline button press

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
            reply_markup=InlineKeyboardMarkup(buttons),
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
            await query.message.reply_text("⚠ Daily reading limit reached.")
            return

        prog["count"] += 1
        prog["episode"] += 1
        save_user_progress()
        await send_episode(query.message.chat_id, user_id, context)

    elif data.startswith("react_"):
        parts = data.split("_")
        story_idx = int(parts[1])
        ep_idx = int(parts[2])
        reaction_type = parts[3]

        key = f"{story_idx}_{ep_idx}"
        reactions.setdefault(key, {"love": 0, "fire": 0})
        reactions[key][reaction_type] += 1
        save_reactions()

        await query.answer(text=f"Reaction '{reaction_type}' recorded!", show_alert=False)

    elif data.startswith("bookmark_"):
        parts = data.split("_")
        story_idx = int(parts[1])
        ep_idx = int(parts[2])
        user_bookmarks = bookmarks.setdefault(user_id, [])
        if [story_idx, ep_idx] not in user_bookmarks:
            user_bookmarks.append([story_idx, ep_idx])
            save_bookmarks()
            await query.answer("✅ Bookmarked!")
        else:
            await query.answer("⚠ Already bookmarked.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("bookmarks", bookmarks_command))
    app.add_handler(CommandHandler("bookmark", add_bookmark))
    app.add_handler(CommandHandler("removebookmark", remove_bookmark))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("random", random_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("editstory", editstory))
    app.add_handler(CommandHandler("stories", list_stories))  # You have this function, keep it
    app.add_handler(CommandHandler("read", read_story))       # Same for this
    app.add_handler(CommandHandler("continue", continue_story))
    app.add_handler(CommandHandler("myprogress", my_progress))
    app.add_handler(CommandHandler("categories", list_categories))
    app.add_handler(CommandHandler("category", category_stories))
    app.add_handler(CommandHandler("reactions", show_reactions))
    app.add_handler(CommandHandler("addstory", add_story))
    app.add_handler(CommandHandler("deleteepisode", delete_episode))

    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started.")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
