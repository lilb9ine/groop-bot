import asyncio
from telegram.ext import ApplicationBuilder

BOT_TOKEN = "7589267392:AAFSu-tjVlJ7u2Zj8bpkITKM3WM3aa5nJ_s"

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add your handlers here, e.g.
    # app.add_handler(CommandHandler("start", start))
    # ... all other handlers ...

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
