import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from supabase import create_client, Client
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_IDS = os.environ.get("ADMIN_IDS", "")  # Comma-separated admin Telegram IDs
ADMIN_IDS = [int(admin.strip()) for admin in ADMIN_IDS.split(",") if admin.strip().isdigit()]

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# State tracking for users uploading stories
user_states = {}

# Helper function to fetch stories
def get_all_stories():
    response = supabase.table("stories").select("*").execute()
    return response.data or []

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to StoryBot!\nUse /categories to view story categories.")

# Categories command
async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stories = get_all_stories()
    categories = sorted(set(story["category"] for story in stories))
    if not categories:
        await update.message.reply_text("No categories available.")
        return

    buttons = [[InlineKeyboardButton(cat, callback_data=f"category:{cat}")] for cat in categories]
    await update.message.reply_text("Choose a category:", reply_markup=InlineKeyboardMarkup(buttons))

# Show stories by category
async def handle_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.split(":", 1)[1]
    stories = get_all_stories()
    filtered = [story for story in stories if story["category"] == category]

    if not filtered:
        await query.edit_message_text("No stories in this category.")
        return

    buttons = [[InlineKeyboardButton(story["title"], callback_data=f"story:{story['id']}")] for story in filtered]
    await query.edit_message_text(f"Stories in {category}:", reply_markup=InlineKeyboardMarkup(buttons))

# Show story and episode
async def handle_story_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    story_id = query.data.split(":", 1)[1]

    response = supabase.table("stories").select("*").eq("id", story_id).execute()
    if not response.data:
        await query.edit_message_text("Story not found.")
        return

    story = response.data[0]
    episodes = json.loads(story["episodes"])
    if not episodes:
        await query.edit_message_text("No episodes available for this story.")
        return

    text = f"📖 *{story['title']}* - Episode 1\n\n{episodes[0]}"
    buttons = []

    if len(episodes) > 1:
        buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"next:{story_id}:1"))

    buttons.append(InlineKeyboardButton("❤️ React", callback_data="react"))
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([buttons]))

# Handle next episode
async def handle_next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, story_id, episode_index = query.data.split(":")
    episode_index = int(episode_index)

    response = supabase.table("stories").select("*").eq("id", story_id).execute()
    if not response.data:
        await query.edit_message_text("Story not found.")
        return

    story = response.data[0]
    episodes = json.loads(story["episodes"])

    if episode_index >= len(episodes):
        await query.edit_message_text("No more episodes.")
        return

    text = f"📖 *{story['title']}* - Episode {episode_index + 1}\n\n{episodes[episode_index]}"
    buttons = []

    if episode_index + 1 < len(episodes):
        buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"next:{story_id}:{episode_index + 1}"))

    buttons.append(InlineKeyboardButton("❤️ React", callback_data="react"))
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([buttons]))

# Handle reactions
async def handle_react_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Thanks for the ❤️!", show_alert=True)

# Upload story (admin only)
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You're not authorized to upload stories.")
        return

    user_states[user_id] = {"step": 1}
    await update.message.reply_text("Send the story title:")

async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_states:
        return

    state = user_states[user_id]
    text = update.message.text

    if state["step"] == 1:
        state["title"] = text
        state["step"] = 2
        await update.message.reply_text("Enter the category:")
    elif state["step"] == 2:
        state["category"] = text
        state["step"] = 3
        await update.message.reply_text("Send the episodes (separated by `||`):")
    elif state["step"] == 3:
        episodes = [ep.strip() for ep in text.split("||") if ep.strip()]
        if not episodes:
            await update.message.reply_text("Please send at least one episode.")
            return
        supabase.table("stories").insert({
            "title": state["title"],
            "category": state["category"],
            "episodes": json.dumps(episodes)
        }).execute()
        await update.message.reply_text("✅ Story uploaded successfully!")
        user_states.pop(user_id)

# Main function
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("categories", categories))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages))
    app.add_handler(CallbackQueryHandler(handle_category_callback, pattern="^category:"))
    app.add_handler(CallbackQueryHandler(handle_story_callback, pattern="^story:"))
    app.add_handler(CallbackQueryHandler(handle_next_callback, pattern="^next:"))
    app.add_handler(CallbackQueryHandler(handle_react_callback, pattern="^react$"))

    app.run_polling()

if __name__ == "__main__":
    main()
