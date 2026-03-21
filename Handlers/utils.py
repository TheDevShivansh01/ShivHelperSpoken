from telegram import Update
from telegram.ext import ContextTypes


async def _safe_reply(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      text: str, parse_mode: str = "HTML", reply_markup=None):
    chat_id = update.effective_chat.id
    try:
        await update.message.reply_text(
            text, parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"[_safe_reply] {e}")