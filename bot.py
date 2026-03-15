from telegram.ext import  Application,filters, CommandHandler,MessageHandler
from Handlers.command import TOKEN, start_command,help_command
from Handlers.command import register_group,add_url,forceregister,broadcast_message
from Handlers.translation import start_translation_command,mystreak_command,adddata_command,cancel_translation_command,difficulty_callback,next_sentence_command,translation_message_handler
from Handlers.common import send_thought_of_the_day,scheduled_send_thought
from Handlers.voice import handle_voice_message
from telegram.ext import CallbackQueryHandler 
import asyncio,time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

def schedule_send_thought_job(app, loop):
    asyncio.run_coroutine_threadsafe(scheduled_send_thought(app), loop)


def main():
    application = Application.builder().token(TOKEN).build()
    # Import

# Inside main(), after existing handlers:
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler("starttranslation", start_translation_command))
    application.add_handler(CommandHandler("next", next_sentence_command))
    application.add_handler(MessageHandler(filters.TEXT  & ~filters.COMMAND,translation_message_handler))
    application.add_handler(CommandHandler("brdmessage", broadcast_message))
    application.add_handler(CommandHandler("addUrl", add_url))
    application.add_handler(CommandHandler("stop", cancel_translation_command))
    application.add_handler(CommandHandler("sendthoughtoftheday", send_thought_of_the_day))
    application.add_handler(CommandHandler("forceregister", forceregister))
    application.add_handler(CommandHandler("mystreak", mystreak_command))
    application.add_handler(CommandHandler("adddata", adddata_command))
    application.add_handler(CallbackQueryHandler(difficulty_callback, pattern="^tg_diff_"))
    scheduler = AsyncIOScheduler(timezone=timezone('Asia/Kolkata'))
    loop = asyncio.get_event_loop()
    scheduler.add_job(schedule_send_thought_job, 'cron', hour=2, minute=32, args=[application, loop])
    scheduler.start()
    application.run_polling()

if __name__ == "__main__":
    print("Bot is running...")
    main()