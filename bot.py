from telegram.ext import  Application,filters, CommandHandler,MessageHandler
from Handlers.command import TOKEN,help_command
from Handlers.command import register_group,add_url,forceregister,broadcast_message
from Handlers.translation import start_translation_command,mystreak_command,adddata_command,cancel_translation_command,difficulty_callback,next_sentence_command,translation_message_handler
from Handlers.common import send_thought_of_the_day,bot_added_to_group_handler,download_report_command,scheduled_send_thought,update_report_command
from Handlers.voice import handle_voice_message
from Handlers.manageTokens import add_tokens_command,start_command,addpara_command,deletepara_command,deletepara_callback,addpara_level_callback
from Handlers.readandrecord import (next_read_and_record_command,mss_back_callback,mss_level_callback,my_speech_score_command,rar_next_prompt_callback,rar_level_callback,rar_score_command,rar_leaderboard_command)
from Commands.Features import features_command, features_callback
from telegram.ext import ChatMemberHandler
from Commands.DailyCurrentAffairs import sendtoday_command
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
    application.add_handler(CommandHandler("record", next_read_and_record_command))
    application.add_handler(CommandHandler("myscore", my_speech_score_command))
    application.add_handler(CommandHandler("addtokens", add_tokens_command))
    application.add_handler(CallbackQueryHandler(mss_level_callback, pattern="^mss_level_"))
    application.add_handler(CallbackQueryHandler(mss_back_callback,  pattern="^mss_back_"))
    application.add_handler(CommandHandler("rarscore",rar_score_command))
    application.add_handler(CommandHandler("topspeaker",rar_leaderboard_command))
    application.add_handler(CallbackQueryHandler(rar_level_callback, pattern="^rar_level_"))
    application.add_handler(CommandHandler("addpara",    addpara_command))
    application.add_handler(CommandHandler("deletepara", deletepara_command))
    application.add_handler(CallbackQueryHandler(addpara_level_callback, pattern="^addpara_level_"))
    application.add_handler(CallbackQueryHandler(deletepara_callback,    pattern="^deletepara_"))
    application.add_handler(CommandHandler("next", next_sentence_command))
    application.add_handler(MessageHandler(filters.TEXT  & ~filters.COMMAND,translation_message_handler))
    application.add_handler(CommandHandler("brdmessagespoken", broadcast_message))
    application.add_handler(CommandHandler("sendtoday", sendtoday_command))
    application.add_handler(ChatMemberHandler(bot_added_to_group_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("addUrl", add_url))
    application.add_handler(CommandHandler("stop", cancel_translation_command))
    application.add_handler(CommandHandler("sendthoughtoftheday", send_thought_of_the_day))
    application.add_handler(CommandHandler("forceregister", forceregister))
    application.add_handler(CommandHandler("mystreak", mystreak_command))
    application.add_handler(CommandHandler("adddata", adddata_command))
    application.add_handler(CommandHandler("features", features_command))
    application.add_handler(CallbackQueryHandler(features_callback, pattern="^feat_"))
    application.add_handler(CommandHandler("downloadreport", download_report_command))
    application.add_handler(CommandHandler("updatereport", update_report_command))
    application.add_handler(CallbackQueryHandler(rar_next_prompt_callback, pattern="^rar_next_prompt$"))
    application.add_handler(CallbackQueryHandler(difficulty_callback, pattern="^tg_diff_"))
    scheduler = AsyncIOScheduler(timezone=timezone('Asia/Kolkata'))
    loop = asyncio.get_event_loop()
    scheduler.add_job(schedule_send_thought_job, 'cron', hour=7, minute=00, args=[application, loop])
    scheduler.start()
    application.run_polling(allowed_updates=["message", "callback_query", "my_chat_member"])

if __name__ == "__main__":
    print("Bot is running...")
    main()