from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from Handlers.utils import _safe_reply


FEATURES_MAIN_TEXT = (
    "✨ <b>Spoken Helper — Features</b>\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Welcome! Spoken Helper helps you improve your English.\n\n"
    "Choose a feature to learn more 👇"
)

FEATURES_MAIN_KEYBOARD = InlineKeyboardMarkup([[
    InlineKeyboardButton("🌐 Translation Game",  callback_data="feat_translation"),
    InlineKeyboardButton("🎙️ Daily Thought",     callback_data="feat_dailythought"),
], [
    InlineKeyboardButton("📚 Read & Record",     callback_data="feat_readrecord"),
    InlineKeyboardButton("📋 All Commands",      callback_data="feat_commands"),
]])


FEAT_TRANSLATION = (
    "🌐 <b>Translation Game</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n\n"
    "Translate Hindi sentences into English and get instant scores!\n\n"
    "🎯 <b>How it works:</b>\n"
    "├ A Hindi sentence is shown\n"
    "├ Type your English translation\n"
    "├ Score ≥55% → your result is shown\n"
    "├ Score ≥90% → next sentence loads automatically\n"
    "└ Use /next to skip any sentence\n\n"
    "📊 <b>Scoring:</b>\n"
    "├ Word match + position scoring\n"
    "├ Hint shown if score is below 100%\n"
    "└ Practice points saved automatically\n\n"
    "🎮 <b>Difficulty Levels:</b>\n"
    "├ 🟢 Easy\n"
    "├ 🟡 Medium\n"
    "└ 🔴 Hard\n\n"
    "⚡ <b>Commands:</b>\n"
    "├ /starttranslation — start the game\n"
    "├ /next — skip to next sentence\n"
    "├ /stop — stop the game\n"
    "└ /mystreak — view your stats"
)

FEAT_DAILYTHOUGHT = (
    "🎙️ <b>Daily Thought — Read Aloud</b>\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Every day a new thought is posted at 7 AM.\n"
    "Read it aloud and send a voice message to build your streak!\n\n"
    "🔥 <b>How Streaks Work:</b>\n"
    "├ Read the daily thought aloud\n"
    "├ Send a voice message in the group\n"
    "├ Match score ≥65% → streak counted\n"
    "├ Consecutive days = longer streak\n"
    "└ One submission per day allowed\n\n"
    "🏆 <b>Badges:</b>\n"
    "├ 🏆 Week Badge — every 7 day streak\n"
    "└ 🥇 Month Badge — every 30 day streak\n\n"
    "📊 <b>Stats tracked:</b>\n"
    "├ Current streak\n"
    "├ Personal best streak\n"
    "├ Week & Month badges\n"
    "└ Match score per attempt\n\n"
    "⚡ <b>Commands:</b>\n"
    "└ /mystreak — view your streak & badges"
)

FEAT_READRECORD = (
    "📚 <b>Read &amp; Record Practice</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n\n"
    "Get a paragraph, read it aloud, send a voice recording\n"
    "and get an instant speech score!\n\n"
    "🎤 <b>How it works:</b>\n"
    "├ Hit /record\n"
    "├ Choose a difficulty level\n"
    "├ Read the paragraph shown\n"
    "├ Send your voice recording\n"
    "└ Get match score + speech rank\n\n"
    "📊 <b>Difficulty Levels:</b>\n"
    "├ 🌱 Easy — short simple sentences\n"
    "├ 📘 Medium — normal paragraphs\n"
    "├ 🔥 Hard — complex vocabulary\n"
    "└ 💎 Advanced — academic level\n\n"
    "🏅 <b>Speech Ranks:</b>\n"
    "├ 🥇 Fluent Speaker   (avg ≥90%)\n"
    "├ 🥈 Confident Reader (avg ≥75%)\n"
    "├ 🥉 Developing Voice (avg ≥60%)\n"
    "├ 📖 Practitioner     (avg ≥40%)\n"
    "└ 🌱 Beginner         (avg &lt;40%)\n\n"  # ← &lt; instead of 
    "📅 <b>Daily Limits:</b>\n"
    "├ 👤 Guest          →  2 sessions/day\n"
    "├ ✅ Channel Member →  10 sessions/day\n"
    "└ 💎 Premium        →  tokens based\n\n"
    "⚡ <b>Commands:</b>\n"
    "├ /record — get next paragraph\n"
    "├ /myscore — view your speech stats\n"
    "└ /topspeaker — group leaderboard"
)

FEAT_COMMANDS = (
    "📋 <b>All Commands</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n\n"

    "🌐 <b>Translation Game</b>\n"
    "├ /starttranslation — start game\n"
    "├ /next — skip sentence\n"
    "├ /stop — stop game\n\n"

    "🎙️ <b>Daily Thought</b>\n"
    "├ /mystreak — streak & badges\n\n"

    "📚 <b>Read &amp; Record</b>\n"
    "├ /record — new paragraph\n"
    "├ /myscore — your speech stats\n"
    "└ /topspeaker — leaderboard\n\n"

    "👤 <b>General</b>\n"
    "├ /features — show all features\n"
    "└ /start — start the bot"
)

BACK_KEYBOARD = InlineKeyboardMarkup([[
    InlineKeyboardButton("⬅️ Back", callback_data="feat_back")
]])


async def features_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await _safe_reply(
            update, context,
            FEATURES_MAIN_TEXT,
            reply_markup=FEATURES_MAIN_KEYBOARD
        )
    except Exception as e:
        print(f"[features_command] {e}")


async def features_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data

    mapping = {
        "feat_translation" : (FEAT_TRANSLATION,      BACK_KEYBOARD),
        "feat_dailythought": (FEAT_DAILYTHOUGHT,      BACK_KEYBOARD),
        "feat_readrecord"  : (FEAT_READRECORD,        BACK_KEYBOARD),
        "feat_commands"    : (FEAT_COMMANDS,          BACK_KEYBOARD),
        "feat_back"        : (FEATURES_MAIN_TEXT,     FEATURES_MAIN_KEYBOARD),
    }

    if data not in mapping:
        return

    text, keyboard = mapping[data]

    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"[features_callback] {e}")