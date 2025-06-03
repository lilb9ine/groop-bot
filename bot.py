import json
import logging
import os
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # replace with your Telegram user ID if needed
DATA_FILE = "stories.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Welcome to the Groop Story Bot!\nUse /stories to see stories or /help for all commands."
    )
")


async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    categories = sorted(set(story["category"] for story in data))
    if not categories:
        await update.message.reply_text("No stories available.")
        return
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=f"cat:{cat}")]
        for cat in categories
    ]
    await update.message.reply_text("Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()

    if query.data.startswith("cat:"):
        category = query.data[4:]
        stories = [s for s in data if s["category"] == category]
        keyboard = [
            [InlineKeyboardButton(s["title"], callback_data=f"story:{s['id']}:0")]
            for s in stories
        ]
        await query.edit_message_text(f"Stories in '{category}':", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("story:"):
        _, story_id, ep_idx = query.data.split(":")
        story = next((s for s in data if s["id"] == story_id), None)
        if not story:
            await query.edit_message_text("Story not found.")
            return
        ep_idx = int(ep_idx)
        total_eps = len(story["episodes"])
        text = f"*{story['title']}* - Episode {ep_idx + 1}/{total_eps}\n\n{story['episodes'][ep_idx]}"
        keyboard = []

        if ep_idx > 0:
            keyboard.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"story:{story_id}:{ep_idx - 1}"))
        if ep_idx < total_eps - 1:
            keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"story:{story_id}:{ep_idx + 1}"))

        reactions = ["❤️", "😂", "😮", "😢"]
        reaction_buttons = [InlineKeyboardButton(r, callback_data=f"react:{r}") for r in reactions]

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([keyboard, reaction_buttons] if keyboard else [reaction_buttons])
        )

    elif query.data.startswith("react:"):
        emoji = query.data.split(":")[1]
        await query.answer(f"You reacted with {emoji}", show_alert=True)


async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to upload stories.")
        return

    try:
        title = context.args[0]
        category = context.args[1]
        episode_texts = " ".join(context.args[2:]).split("|||")

        new_story = {
            "id": str(len(load_data()) + 1),
            "title": title,
            "category": category,
            "episodes": episode_texts
        }

        data = load_data()
        data.append(new_story)
        save_data(data)
        await update.message.reply_text(f"Story '{title}' uploaded in category '{category}'.")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error uploading story. Format:\n/upload <title> <category> <ep1|||ep2|||ep3>")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
   app.add_handler(CommandHandler("stories", categories))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()


if __name__ == "__main__":
    main()
