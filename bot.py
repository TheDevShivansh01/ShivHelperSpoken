from telegram.ext import  Application,filters, CommandHandler,MessageHandler, PollAnswerHandler, CallbackQueryHandler, ContextTypes
from Handlers.command import TOKEN,add_promo,botManagementGroupId,MNTH_SCORE_FILE, start_command,start_game_command,help_command,handle_difficulty_selection,handle_type_selection,handle_time_selection,handle_button_click,handle_New_button_click,handle_poll_answer,my_rank
from Handlers.command import register_group,handle_samplePaperType_selection,handle_SamplePaper_selection,handle_SamplePaper_button_click,add_url,forceregister,month_topper,handle_allsizzlescore,topgrp_scorer,all_time_topper,cancel_quiz_command,handle_updatesizzlescore,handle_jsonFile,send_message,add_message,add_time,add_file,show_message,broadcast_message
from Handlers.common import stopupsctopicCommand,allowupsctopicCommand,send_word_of_the_day,schedule_send_UpscTopic,scheduled_send_word,shuffle_all_files_inplace,shuffle_command
import asyncio,datetime,calendar
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

def schedule_send_word_job(app, loop):
    asyncio.run_coroutine_threadsafe(scheduled_send_word(app), loop)

def schedule_send_UpscTopic_job(app, loop):
    
    asyncio.run_coroutine_threadsafe(schedule_send_UpscTopic(app), loop)
def is_last_day_of_month():
    today = datetime.date.today()
    return today.day == calendar.monthrange(today.year, today.month)[1]

def reset_score_file():
    try:
        df = pd.read_excel(MNTH_SCORE_FILE)
        cleared_df = df.iloc[0:0]
        cleared_df.to_excel(MNTH_SCORE_FILE, index=False)
        print("✅ Score file reset (only header retained).")
    except Exception as e:
        print(f"❌ Failed to reset score file: {e}")

def check_and_reset_scores():
    if is_last_day_of_month():
        reset_score_file()

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler('startquiz', start_game_command))
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CallbackQueryHandler(handle_difficulty_selection, pattern='^difficulty_'))
    application.add_handler(CallbackQueryHandler(handle_type_selection, pattern='^type_'))
    application.add_handler(CallbackQueryHandler(handle_SamplePaper_selection, pattern='^sample_'))
    application.add_handler(CallbackQueryHandler(handle_time_selection, pattern='^time_'))
    application.add_handler(CallbackQueryHandler(handle_SamplePaper_button_click, pattern='^sampletype_'))
    application.add_handler(CallbackQueryHandler(handle_samplePaperType_selection, pattern='^sampletime_'))
    application.add_handler(CallbackQueryHandler(handle_button_click, pattern=r'^\d+$'))
    application.add_handler(CallbackQueryHandler(handle_New_button_click, pattern= '^New_'))
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    application.add_handler(CommandHandler("myrank", my_rank))
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), register_group))
    application.add_handler(CommandHandler("topgrpscorer", topgrp_scorer))
    application.add_handler(CommandHandler("alltimetopper", all_time_topper))
    application.add_handler(CommandHandler("rankers", month_topper))
    application.add_handler(CommandHandler('cancelquiz', cancel_quiz_command))
    application.add_handler(CommandHandler('updatesizzlescore', handle_updatesizzlescore))
    application.add_handler(CommandHandler('updateallscore', handle_allsizzlescore))
    application.add_handler(CommandHandler('updategroupid', handle_jsonFile))
    application.add_handler(CommandHandler("sendmessagetest", send_message))
    application.add_handler(CommandHandler("addmessage", add_message))
    application.add_handler(CommandHandler("addtime", add_time))
    application.add_handler(CommandHandler("addfile", add_file))
    application.add_handler(CommandHandler("addpromo", add_promo))
    application.add_handler(CommandHandler("showmessage", show_message))
    application.add_handler(CommandHandler("brdmessage", broadcast_message))
    application.add_handler(CommandHandler("addUrl", add_url))
    application.add_handler(CommandHandler("shuffle", shuffle_command))
    application.add_handler(CommandHandler("sendwordoftheday", send_word_of_the_day))
    # application.add_handler(CommandHandler("stoptopic", stopupsctopicCommand))
    # application.add_handler(CommandHandler("allowtopic", allowupsctopicCommand))
    application.add_handler(CommandHandler("forceregister", forceregister))
    scheduler = AsyncIOScheduler(timezone=timezone('Asia/Kolkata'))
    loop = asyncio.get_event_loop()
    scheduler.add_job(schedule_send_word_job, 'cron', hour=8, minute=00, args=[application, loop])
  #  scheduler.add_job(schedule_send_UpscTopic_job, 'cron', hour=10, minute=30, args=[application, loop])
    scheduler.add_job(check_and_reset_scores, 'cron', hour=00, minute=5)

    scheduler.start()
    application.run_polling()


if __name__ == "__main__":
    print("Bot is running...")
    main()