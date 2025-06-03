import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from supabase import create_client, Client

# Get secrets from environment variables (set on Render)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Browse Stories", callback_data="browse")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to the Story Bot!", reply_markup=reply_markup)

# Handle button clicks
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "browse":
        # Show list of story categories
        stories = supabase.table("stories").select("*").execute().data
        if not stories:
            await query.edit_message_text("No stories available yet.")
            return
        buttons = []
        for story in stories:
            buttons.append([InlineKeyboardButton(story["title"], callback_data=f"story_{story['id']}")])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("Choose a story:", reply_markup=reply_markup)

    elif data.startswith("story_"):
        story_id = int(data.split("_")[1])
        story = supabase.table("stories").select("*").eq("id", story_id).single().execute().data
        if story:
            episodes = story["episodes"]
            if episodes:
                await query.edit_message_text(f"*{story['title']} - Episode 1:*\n\n{episodes[0]}", parse_mode="Markdown")
            else:
                await query.edit_message_text("This story has no episodes yet.")
        else:
            await query.edit_message_text("Story not found.")

# Start the bot
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
