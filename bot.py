import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from supabase import create_client

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Conversation states
WAITING_FOR_TITLE, WAITING_FOR_CATEGORY, WAITING_FOR_EPISODES = range(3)

# Upload story flow
async def upload_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ You are not authorized to use this command.")
        return ConversationHandler.END

    await update.message.reply_text("📤 Send the *story title*:", parse_mode="Markdown")
    return WAITING_FOR_TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("📚 Send the *story category* (e.g. horror, romance, etc.):", parse_mode="Markdown")
    return WAITING_FOR_CATEGORY

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["category"] = update.message.text
    await update.message.reply_text("📝 Send the *episodes*, separated by `---` (3 dashes):", parse_mode="Markdown")
    return WAITING_FOR_EPISODES

async def get_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    episodes = update.message.text.split("---")
    title = context.user_data["title"]
    category = context.user_data["category"]

    data = {
        "title": title.strip(),
        "category": category.strip(),
        "episodes": [e.strip() for e in episodes if e.strip()]
    }

    try:
        supabase.table("stories").insert(data).execute()
        await update.message.reply_text("✅ Story uploaded successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to upload: {e}")

    return ConversationHandler.END

async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Upload cancelled.")
    return ConversationHandler.END

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the story bot! Use /upload to add a new story (admin only).")

# Main
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Upload story handler
    upload_conv = ConversationHandler(
        entry_points=[CommandHandler("upload", upload_story)],
        states={
            WAITING_FOR_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            WAITING_FOR_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
            WAITING_FOR_EPISODES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_episodes)],
        },
        fallbacks=[CommandHandler("cancel", cancel_upload)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(upload_conv)

    application.run_polling()
