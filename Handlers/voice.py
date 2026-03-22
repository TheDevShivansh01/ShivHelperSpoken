import os
import asyncio
import tempfile
import speech_recognition as sr
import pandas as pd
from datetime import date
from pydub import AudioSegment
from Handlers import readandrecord as rar_module
from Handlers.readandrecord import (
    handle_word_practice_voice,   
    word_practice_state,          
)
from fuzzywuzzy import fuzz
from telegram import Update
from telegram.ext import ContextTypes

GROUP_SEND_ID = -1002114430690
# ── Paths ─────────────────────────────────────────────────────────────────────
STREAK_EXCEL_PATH  = "UserScore/user_streaks.xlsx"
THOUGHT_EXCEL_PATH = "UserScore/thoughts.xlsx"

recognizer = sr.Recognizer()

# ── Streak helpers ─────────────────────────────────────────────────────────────

def _load_streak_df() -> pd.DataFrame:
    if os.path.exists(STREAK_EXCEL_PATH):
        return pd.read_excel(STREAK_EXCEL_PATH)
    os.makedirs(os.path.dirname(STREAK_EXCEL_PATH), exist_ok=True)
    return pd.DataFrame(columns=[
        'user_id', 'username', 'current_streak',
        'max_streak', 'last_date', 'streak7_count', 'streak30_count'
    ])


def _already_submitted_today(user_id: int, df: pd.DataFrame) -> bool:
    mask = df['user_id'] == user_id
    if not mask.any():
        return False
    last_date = pd.to_datetime(df[mask].iloc[0]['last_date']).date()
    return last_date == date.today()     

def _update_streak(user_id: int, username: str, df: pd.DataFrame):
    today = date.today()
    mask  = df['user_id'] == user_id

    if mask.any():
        idx       = df[mask].index[0]
        last_date = pd.to_datetime(df.at[idx, 'last_date']).date()

        if (today - last_date).days == 1:
            df.at[idx, 'current_streak'] += 1
        else:
            df.at[idx, 'current_streak'] = 1

        cs = int(df.at[idx, 'current_streak'])
        df.at[idx, 'username']       = username
        df.at[idx, 'last_date']      = today
        df.at[idx, 'max_streak']     = max(int(df.at[idx, 'max_streak']), cs)
        df.at[idx, 'streak7_count']  = cs // 7
        df.at[idx, 'streak30_count'] = cs // 30

    else:
        cs = 1
        new_row = {
            'user_id'       : user_id,
            'username'      : username,
            'current_streak': cs,
            'max_streak'    : cs,
            'last_date'     : today,
            'streak7_count' : 0,
            'streak30_count': 0,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_excel(STREAK_EXCEL_PATH, index=False)
    return df, cs


async def _update_streak_and_send(user_id: int, username: str, df: pd.DataFrame, context):
    df, cs = _update_streak(user_id, username, df)
    try:
        with open(STREAK_EXCEL_PATH, 'rb') as f:
            await context.bot.send_document(
                chat_id=GROUP_SEND_ID,
                document=f,
                filename="user_streaks.xlsx",
                caption=f"📊 Streak updated — <b>{username}</b> | Streak: <b>{cs}</b>",
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"[Voice] Failed to send streak file: {e}")
    return df, cs

# ── Today's thought ────────────────────────────────────────────────────────────

def _get_todays_thought() -> str | None:
    if not os.path.exists(THOUGHT_EXCEL_PATH):
        return None
    df = pd.read_excel(THOUGHT_EXCEL_PATH)
    
    today_str = str(date.today())  # "2026-03-16"
    today_df  = df[df['sentdate'].astype(str) == today_str]
    
    if today_df.empty:
        return None  
    
    return str(today_df.iloc[0]['thought']).strip()


# ── OGG → WAV conversion (Google SR needs WAV) ────────────────────────────────

def _convert_ogg_to_wav(ogg_path: str) -> str:
    wav_path = ogg_path.replace('.ogg', '.wav')
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(wav_path, format='wav')
    return wav_path


# ── Transcribe using Google Speech Recognition ────────────────────────────────

def _transcribe(wav_path: str) -> str | None:
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio_data, language="en-IN")
    except sr.UnknownValueError:
        return None       # couldn't understand audio
    except sr.RequestError as e:
        print(f"[Voice] Google SR API error: {e}")
        return None


# ── Main handler ───────────────────────────────────────────────────────────────
async def handle_voice_message(update: Update, context):
    message = update.message
    if not message or not message.voice:
        return
    chat_id=message.chat.id
    user     = message.from_user
    user_id  = user.id
    username = user.username or user.first_name or f"user_{user_id}"

    ogg_path = None
    wav_path = None

    try:
        # ── Download .ogg from Telegram ────────────────────────────────────────
        voice_file = await context.bot.get_file(message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
            ogg_path = tmp.name
        await voice_file.download_to_drive(ogg_path)

        # ── Convert + Transcribe ───────────────────────────────────────────────
        loop = asyncio.get_event_loop()

        def process():
            wav = _convert_ogg_to_wav(ogg_path)
            text = _transcribe(wav)
            return wav, text

        wav_path, transcribed = await loop.run_in_executor(None, process)

        if not transcribed:
            try:
                await message.reply_text(
                    "🎙️ Couldn't understand your voice. Please speak clearly and try again!"
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=message.chat.id,
                    text="🎙️ Couldn't understand your voice. Please speak clearly and try again!"
                )
            return
        

        if user_id in word_practice_state:
            handled = await handle_word_practice_voice(update, context, transcribed)
            if handled:
                return

        # ── RAR CHECK FIRST — before any daily thought logic ──────────────────
        if rar_module.rar_chat_state.get(chat_id) and rar_module.rar_chat_state[chat_id].get("paragraph"):
            handled = await rar_module.handle_rar_voice(update, context, transcribed)
            if handled:
                return
        # ──────────────────────────────────────────────────────────────────────

        # ── Daily Thought checks (only if NOT a RAR voice) ────────────────────
        thought = _get_todays_thought()
        if not thought:
            return

        df = _load_streak_df()
        if _already_submitted_today(user_id, df):
            return

        # ── Fuzzy match ────────────────────────────────────────────────────────
        match_score = fuzz.token_set_ratio(
            transcribed.lower(),
            thought.lower()
        )

        if match_score >= 65:
            _, current_streak = await _update_streak_and_send(user_id, username, df, context)
            streak7  = current_streak // 7
            streak30 = current_streak // 30
            badge    = "🔥" * min(current_streak, 5)
            try:
                await message.reply_text(
                    f"✅ <b>Well done, {username}!</b> {badge}\n\n"
                    f"📖 Match Score    : <b>{match_score}%</b>\n"
                    f"📅 Current Streak : <b>{current_streak} day(s)</b>\n"
                    f"🏆 Week Badges  (÷7)  : <b>{streak7}</b>\n"
                    f"🥇 Month Badges (÷30) : <b>{streak30}</b>",
                    parse_mode="HTML"
                )
            except Exception as ex:
                await context.bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        f"✅ <b>Well done, {username}!</b> {badge}\n\n"
                        f"📖 Match Score    : <b>{match_score}%</b>\n"
                        f"📅 Current Streak : <b>{current_streak} day(s)</b>\n"
                        f"🏆 Week Badges  (÷7)  : <b>{streak7}</b>\n"
                        f"🥇 Month Badges (÷30) : <b>{streak30}</b>"
                    ),
                    parse_mode="HTML"
                )

    except Exception as e:
        print(f"[Voice] Error for {username}: {e}")

    finally:
        for path in [ogg_path, wav_path]:
            if path and os.path.exists(path):
                os.unlink(path)