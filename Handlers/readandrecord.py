import os
import re
import asyncio
import random
import pandas as pd
from datetime import date, datetime
from difflib import SequenceMatcher
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from Handlers.manageTokens  import _get_user_tokens,_deduct_token
from telegram.error import BadRequest, Forbidden, TimedOut
from Handlers.utils import _safe_reply

READING_FILEPATH  = "Data/reading_paragraphs.xlsx"
PREMIUM_TOKEN_PATH = "UserScore/premium_tokens.xlsx"
SPEECH_SCORE_PATH = "UserScore/speechscore.xlsx"
QR_CODE_PATH       = "Data/payment.jpg" 
RAR_DAILY_PATH    = "UserScore/rar_daily_usage.xlsx"

CHANNEL_USERNAME   = "@currentaffairs_04"
CHANNEL_INVITE_URL = "https://t.me/currentaffairs_04"
PREMIUM_CONTACT    = "https://t.me/O000000000O00000000O"

PREMIUM_PRICE      = "₹10"
PREMIUM_TOKENS     = 50  # ← apna QR image yahan rakho
BOT_USERNAME       = "spoken_helper_bot"



DAILY_LIMIT_NON_MEMBER = 2
DAILY_LIMIT_MEMBER     = 10
MIN_SCORE_TO_COUNT     = 50

LEVEL_LABELS = {
    "easy"    : "🟢 Easy",
    "medium"  : "🟡 Medium",
    "hard"    : "🔴 Hard",
    "advanced": "🟣 Advanced",
}

SCORE_LEVEL_LABELS = {
    "easy"    : "Easy",
    "medium"  : "Medium",
    "hard"    : "Hard",
    "advanced": "Advanced",
}

LEVEL_COLORS = {
    "easy"    : "🌱",
    "medium"  : "📘",
    "hard"    : "🔥",
    "advanced": "💎",
}

rar_chat_state: dict = {}

    
# ── Excel helpers ─────────────────────────────────────────────────────────────
def _load_reading_df(level: str) -> pd.DataFrame:
    if not os.path.exists(READING_FILEPATH):
        return pd.DataFrame(columns=["srno", "paragraph", "level"])
    df = pd.read_excel(READING_FILEPATH)
    # remove spaces from col names: "Sr No" → "srno"
    df.columns = [c.strip().lower().replace(" ", "") for c in df.columns]
    df = df[df["level"].str.strip().str.lower() == level.lower()]
    return df.reset_index(drop=True)

def _load_speech_score_df() -> pd.DataFrame:
    if os.path.exists(SPEECH_SCORE_PATH):
        df = pd.read_excel(SPEECH_SCORE_PATH)
        # ── ensure new columns exist in old files too ──────────────────────
        for lvl in ["easy", "medium", "hard", "advanced"]:
            for col in [f"{lvl}_attempts", f"{lvl}_total", f"{lvl}_avg", f"{lvl}_best"]:
                if col not in df.columns:
                    df[col] = 0.0
        return df
    os.makedirs(os.path.dirname(SPEECH_SCORE_PATH), exist_ok=True)
    return pd.DataFrame(columns=[
        "srno", "userid", "chatid", "username",
        # overall
        "speechscore", "attempts", "avg_score", "last_updated",
        # easy
        "easy_attempts", "easy_total", "easy_avg", "easy_best",
        # medium
        "medium_attempts", "medium_total", "medium_avg", "medium_best",
        # hard
        "hard_attempts", "hard_total", "hard_avg", "hard_best",
        # advanced
        "advanced_attempts", "advanced_total", "advanced_avg", "advanced_best",
    ])

async def _get_user_limit_info(context, user_id: int) -> dict:
    tokens    = _get_user_tokens(user_id)
    is_member = await _is_channel_member(context, user_id)

    # ── daily free limit (based on membership) ────────────────────────────
    if is_member:
        free_limit = DAILY_LIMIT_MEMBER       # 10
        plan       = "Channel Member"
    else:
        free_limit = DAILY_LIMIT_NON_MEMBER   # 2
        plan       = "Guest"

    today_count   = _get_today_count(user_id)
    free_remaining = max(0, free_limit - today_count)

    # ── tokens are on TOP of free sessions ────────────────────────────────
    has_tokens = tokens > 0
    is_premium = has_tokens

    if is_premium:
        plan = "Premium" if not is_member else "Member + Premium"
        # total remaining = free sessions left + tokens
        remaining   = free_remaining + tokens
        daily_limit = free_limit + tokens     # just for display
    else:
        remaining   = free_remaining
        daily_limit = free_limit

    return {
        "daily_limit"   : daily_limit,
        "today_count"   : today_count,
        "free_remaining": free_remaining,
        "remaining"     : remaining,
        "plan"          : plan,
        "is_premium"    : is_premium,
        "is_member"     : is_member,
        "tokens"        : tokens,
    }

def _save_speech_score(user_id: int, chat_id: int, username: str,
                       score: float, level: str):
    df   = _load_speech_score_df()
    mask = (df["userid"] == user_id) & (df["chatid"] == chat_id)
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")

    lvl_att   = f"{level}_attempts"
    lvl_total = f"{level}_total"
    lvl_avg   = f"{level}_avg"
    lvl_best  = f"{level}_best"

    if mask.any():
        # ── overall ───────────────────────────────────────────────────────
        old_total    = float(df.loc[mask, "speechscore"].values[0])
        old_att      = int(df.loc[mask, "attempts"].values[0])
        new_total    = old_total + score
        new_att      = old_att + 1

        df.loc[mask, "speechscore"]   = new_total
        df.loc[mask, "attempts"]      = new_att
        df.loc[mask, "avg_score"]     = round(new_total / new_att, 1)
        df.loc[mask, "username"]      = username
        df.loc[mask, "last_updated"]  = now

        # ── level-wise ────────────────────────────────────────────────────
        old_lvl_total = float(df.loc[mask, lvl_total].values[0])
        old_lvl_att   = int(df.loc[mask, lvl_att].values[0])
        old_lvl_best  = float(df.loc[mask, lvl_best].values[0])
        new_lvl_total = old_lvl_total + score
        new_lvl_att   = old_lvl_att + 1

        df.loc[mask, lvl_total] = new_lvl_total
        df.loc[mask, lvl_att]   = new_lvl_att
        df.loc[mask, lvl_avg]   = round(new_lvl_total / new_lvl_att, 1)
        df.loc[mask, lvl_best]  = max(old_lvl_best, score)

    else:
        new_row = {
            "srno"        : int(df["srno"].max()) + 1 if not df.empty else 1,
            "userid"      : user_id,
            "chatid"      : chat_id,
            "username"    : username,
            "speechscore" : score,
            "attempts"    : 1,
            "avg_score"   : score,
            "last_updated": now,
            # all levels default 0
            "easy_attempts": 0, "easy_total": 0.0,
            "easy_avg"     : 0.0, "easy_best": 0.0,
            "medium_attempts": 0, "medium_total": 0.0,
            "medium_avg"     : 0.0, "medium_best": 0.0,
            "hard_attempts": 0, "hard_total": 0.0,
            "hard_avg"     : 0.0, "hard_best": 0.0,
            "advanced_attempts": 0, "advanced_total": 0.0,
            "advanced_avg"     : 0.0, "advanced_best": 0.0,
        }
        # set the current level values
        new_row[lvl_att]   = 1
        new_row[lvl_total] = score
        new_row[lvl_avg]   = score
        new_row[lvl_best]  = score

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_excel(SPEECH_SCORE_PATH, index=False)


def _get_user_speech_stats(user_id: int, chat_id: int) -> dict:
    """Returns overall + per-level stats. No calculation needed at read time."""
    df   = _load_speech_score_df()
    mask = (df["userid"] == user_id) & (df["chatid"] == chat_id)

    if not mask.any():
        empty_lvl = {"attempts": 0, "avg": 0.0, "best": 0.0, "total": 0.0}
        return {
            "total_score": 0.0, "attempts": 0, "avg_score": 0.0,
            "easy": empty_lvl, "medium": empty_lvl,
            "hard": empty_lvl, "advanced": empty_lvl,
        }

    row = df[mask].iloc[0]

    def lvl_data(lvl):
        return {
            "attempts": int(row[f"{lvl}_attempts"]),
            "avg"     : round(float(row[f"{lvl}_avg"]),   1),
            "best"    : round(float(row[f"{lvl}_best"]),  1),
            "total"   : round(float(row[f"{lvl}_total"]), 1),
        }

    return {
        "total_score": round(float(row["speechscore"]), 1),
        "attempts"   : int(row["attempts"]),
        "avg_score"  : round(float(row["avg_score"]), 1),
        "easy"       : lvl_data("easy"),
        "medium"     : lvl_data("medium"),
        "hard"       : lvl_data("hard"),
        "advanced"   : lvl_data("advanced"),
    }

# ── Daily usage helpers (count deducted on voice send, not on command) ─────────
def _load_daily_df() -> pd.DataFrame:
    if os.path.exists(RAR_DAILY_PATH):
        df = pd.read_excel(RAR_DAILY_PATH)
        df["usage_date"] = pd.to_datetime(df["usage_date"]).dt.date
        return df
    os.makedirs(os.path.dirname(RAR_DAILY_PATH), exist_ok=True)
    return pd.DataFrame(columns=["userid", "usage_date", "count"])


def _get_today_count(user_id: int) -> int:
    df    = _load_daily_df()
    today = date.today()
    mask  = (df["userid"] == user_id) & (df["usage_date"] == today)
    return int(df[mask].iloc[0]["count"]) if mask.any() else 0


def _increment_daily_count(user_id: int):
    """Called only when a valid voice recording is submitted (score >= 50)."""
    df    = _load_daily_df()
    today = date.today()
    mask  = (df["userid"] == user_id) & (df["usage_date"] == today)
    if mask.any():
        df.loc[mask, "count"] += 1
    else:
        df = pd.concat([df, pd.DataFrame([{
            "userid": user_id, "usage_date": today, "count": 1
        }])], ignore_index=True)
    df.to_excel(RAR_DAILY_PATH, index=False)


# ── Channel check ─────────────────────────────────────────────────────────────
async def _is_channel_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


# ── Score utils ───────────────────────────────────────────────────────────────
def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _similarity_score(a: str, b: str) -> float:
    a, b = _normalize(a), _normalize(b)
    if a == b:
        return 100.0
    a_words, b_words = set(a.split()), set(b.split())
    union   = a_words | b_words
    jaccard = len(a_words & b_words) / len(union) if union else 0.0
    char_ratio = SequenceMatcher(None, a, b).ratio()
    return round((jaccard * 0.6 + char_ratio * 0.4) * 100, 1)


def _speech_rank(avg: float) -> str:
    if avg >= 95:   return "🥇 Fluent Speaker"
    elif avg >= 85: return "🥈 Confident Reader"
    elif avg >= 70: return "🥉 Developing Voice"
    elif avg >= 60: return "📖 Practitioner"
    else:           return "🌱 Beginner"


# ── Paragraph template (matches Thought of the Day style) ─────────────────────
def _build_paragraph_message(level: str, srno: int, paragraph: str) -> str:
    label = LEVEL_LABELS.get(level, level.capitalize())
    icon  = LEVEL_COLORS.get(level, "📄")
    return (
        f"📚 <b>Read &amp; Record</b> 📚\n\n"
        f"{icon} <b>Level:</b> <i>{label}</i>\n\n"
        f"📝 <b>Paragraph:</b>\n"
        f"           <i>{paragraph}</i>\n\n"
        f"🎤 Now Record the above paragraph!! 💡"
    )

async def next_read_and_record_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id  = update.effective_user.id
        chat_id  = update.effective_chat.id
       
        info = await _get_user_limit_info(context, user_id)
        if info["remaining"] <= 0:
            await _send_limit_reached_msg(update, context, info)
            return
        
        existing = rar_chat_state.get(chat_id)
        if existing and existing.get("paragraph"):
            await _safe_reply(update, context,
                "⏳ <b>A paragraph is already active!</b>\n\nEveryone record it first.")
            return

      

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🟢 Easy",     callback_data="rar_level_easy"),
            InlineKeyboardButton("🟡 Medium",   callback_data="rar_level_medium"),
        ], [
            InlineKeyboardButton("🔴 Hard",     callback_data="rar_level_hard"),
            InlineKeyboardButton("🟣 Advanced", callback_data="rar_level_advanced"),
        ]])

        msg = (
            f"📚 <b>Read &amp; Record</b> 📚\n\n"
            f"{info['plan']}  |  Tokens left: <b>{info['remaining']}/{info['daily_limit']}</b>\n\n"
            f"Choose a difficulty level:"
        )
        await _safe_reply(update, context, msg, reply_markup=keyboard)

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[next_read_and_record_command] {e}")
    except Exception as e:
        print(f"[next_read_and_record_command] Unexpected: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Callback: level button pressed
#  Does NOT increment daily count — that happens on voice submission
async def rar_level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        await query.answer()
    except Exception:
        pass

    level = query.data.replace("rar_level_", "").lower()
    if level not in LEVEL_LABELS:
        try:
            await query.edit_message_text("❌ Invalid level. Please try again.")
        except Exception:
            await context.bot.send_message(chat_id=chat_id,
                                           text="❌ Invalid level. Please try again.")
        return
    
    # ── already active paragraph in this chat ─────────────────────────────
    existing = rar_chat_state.get(chat_id)
    
    if existing and existing.get("paragraph"):
        try:
            await query.answer(
                "⏳ A paragraph is already active! Everyone record first.",
                show_alert=True
            )
        except Exception:
            pass
        return

    # ── load paragraph ─────────────────────────────────────────────────────
    try:
        df = _load_reading_df(level)
    except Exception as e:
        print(f"[rar_level_callback] Load error: {e}")
        try:
            await query.edit_message_text("❌ Could not load paragraphs. Please try again.")
        except Exception:
            await context.bot.send_message(chat_id=chat_id,
                                           text="❌ Could not load paragraphs. Please try again.")
        return

    if df.empty:
        try:
            await query.edit_message_text(f"❌ No paragraphs found for {LEVEL_LABELS[level]}.")
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id, text=f"❌ No paragraphs found for {LEVEL_LABELS[level]}.")
        return

    last_srno  = rar_chat_state.get(chat_id, {}).get("srno")
    
    candidates = df[df["srno"] != last_srno] if last_srno else df
    if candidates.empty:
        candidates = df

    row       = candidates.sample(1).iloc[0]
    srno      = int(row["srno"])
    paragraph = str(row["paragraph"]).strip()

    # ── save chat-level session ────────────────────────────────────────────
    rar_chat_state[chat_id] = {
        "paragraph"     : paragraph,
        "level"         : level,
        "srno"          : srno,
        "recorded_users": set(),   # tracks who already recorded this paragraph
    }
    msg = _build_paragraph_message(level, srno, paragraph)
    try:
        await query.edit_message_text(msg, parse_mode="HTML")
    except Exception:
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
        except Exception as e:
            print(f"[rar_level_callback] Could not send paragraph: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  Voice handler — called from voice.py
# ══════════════════════════════════════════════════════════════════════════════
# ── handle_rar_voice ──────────────────────────────────────────────────────────
async def handle_rar_voice(
    update    : Update,
    context   : ContextTypes.DEFAULT_TYPE,
    transcript: str,
) -> bool:
    try:
        user     = update.effective_user
        user_id  = user.id
        username = user.username or user.first_name or str(user_id)
        chat_id  = update.effective_chat.id

        session = rar_chat_state.get(chat_id)
        if not session or not session.get("paragraph"):
            return False

        paragraph = session["paragraph"]
        level     = session["level"]
        srno      = session["srno"]

        # ── score pehle calculate karo ─────────────────────────────────────
        score = _similarity_score(transcript, paragraph)
        if score < MIN_SCORE_TO_COUNT:
            return True   # silent — no limit deducted

        # ── limit check — token > channel > guest ──────────────────────────
        info        = await _get_user_limit_info(context, user_id)
        today_count = info["today_count"]
        daily_limit = info["daily_limit"]
        remaining   = info["remaining"]

        if info["remaining"] <= 0:
            await _send_limit_reached_msg(update, context, info)
            return
        # ── deduct session + token if premium ─────────────────────────────
        if info["free_remaining"] > 0:
            _increment_daily_count(user_id)
        elif info["is_premium"] and info["tokens"] > 0:
            _deduct_token(user_id)
        
        new_remaining = max(0, info["remaining"] - 1)  # only deduct token if premium user
        _save_speech_score(user_id, chat_id, username, score, level)
        session["recorded_users"].add(user_id)

        # remaining after this deduction
        new_remaining = max(0, remaining - 1)

        stats = _get_user_speech_stats(user_id, chat_id)
        rank  = _speech_rank(stats["avg_score"])

        if score >= 90:   score_badge = "🌟 Excellent!"
        elif score >= 75: score_badge = "✅ Great job!"
        elif score >= 60: score_badge = "👍 Good effort!"
        else:             score_badge = "📈 Keep practising!"

        level_label = LEVEL_LABELS.get(level, level.capitalize())

        # token remaining show karo if premium
        if info["is_premium"]:
            tokens_left = _get_user_tokens(user_id)
            session_line = (
                f"📅 <b>Sessions Today</b>\n"
                f"├ 🔄 Free Left    →  <b>{max(0, info['free_remaining'] - 1)}/{DAILY_LIMIT_MEMBER if info['is_member'] else DAILY_LIMIT_NON_MEMBER}</b>\n"
                f"├ 🎟️ Tokens Left  →  <b>{tokens_left}</b>\n"
                f"└ 📊 Total Left   →  <b>{new_remaining}</b>\n"
            )
        else:
            session_line = (
                f"📅 <b>Sessions Today</b>\n"
                f"└ 🔄 Remaining  →  <b>{new_remaining}/{info['daily_limit']}</b>  {info['plan']}\n"
            )

        reply = (
            f"🎙️ <b>Read &amp; Record — Result</b>\n"
            f"{'━' * 20}\n\n"
            f"👤 <b>{username}</b>  |  {level_label}\n\n"
            f"📊 <b>This Attempt</b>\n"
            f"├ 🎯 Match Score  →  <b>{score}%</b>  {score_badge}\n\n"
            f"📈 <b>Your Overall Stats</b>\n"
            f"├ ⭐ Total Points  →  <b>{stats['total_score']}</b>\n"
            f"├ 🔁 Attempts      →  <b>{stats['attempts']}</b>\n"
            f"├ 📉 Avg Score     →  <b>{stats['avg_score']}%</b>\n"
            f"└ 🏅 Speech Rank   →  {rank}\n\n"
            f"{session_line}"
        )
        next_keyboard = None
        if new_remaining > 0:
            next_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Next Read & Record",
                                     callback_data="rar_next_prompt")
            ]])

        await _safe_reply(update, context, reply, reply_markup=next_keyboard)
        return True

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[handle_rar_voice] {e}")
        return False
    except Exception as e:
        print(f"[handle_rar_voice] Unexpected: {e}")
        return False
    

async def _send_limit_reached_msg(update, context, info: dict):
    is_member = info["plan"] == "✅ Channel Member"

    if not is_member and not info["is_premium"]:
        msg = (
            f"⚠️ <b>Daily Limit Reached!</b>\n\n"
            f"You've used your <b>{DAILY_LIMIT_NON_MEMBER} free</b> sessions today.\n\n"
            f"🚀 Join our channel for <b>{DAILY_LIMIT_MEMBER} sessions/day</b> free!\n\n"
            f"💎 <b>Premium — {PREMIUM_PRICE} = {PREMIUM_TOKENS} Tokens</b>"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("👉 Join Channel (Free)", url=CHANNEL_INVITE_URL),
        ], [
            InlineKeyboardButton(
                f"💎 Buy Premium",
                url=f"https://t.me/{BOT_USERNAME}?start=premium"
            ),
        ]])
    else:
        msg = (
            f"⚠️ <b>Daily Limit Reached!</b>\n\n"
            f"You've used all <b>{info['daily_limit']} sessions</b> today.\n\n"
            f"💎 <b>Premium — {PREMIUM_PRICE} = {PREMIUM_TOKENS} Tokens</b>"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                f"💎 Buy Premium",
                url=f"https://t.me/{BOT_USERNAME}?start=premium"
            ),
        ]])

    if update.message:
        await _safe_reply(update, context, msg, reply_markup=keyboard)
    else:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=msg, parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"[_send_limit_reached_msg] {e}")
#  Callback: "▶️ Next Read & Record" button in result message
# ══════════════════════════════════════════════════════════════════════════════
async def rar_next_prompt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        await query.answer()
    except Exception:
        pass

    # ✅ FIX — clear old chat session so new paragraph can be loaded
    rar_chat_state.pop(chat_id, None)

    is_member   = await _is_channel_member(context, user_id)
    today_count = _get_today_count(user_id)
    daily_limit = DAILY_LIMIT_MEMBER if is_member else DAILY_LIMIT_NON_MEMBER
    remaining   = max(0, daily_limit - today_count)

    if remaining <= 0:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        is_member = await _is_channel_member(context, user_id)
        if not is_member:
            msg = (
                f"⚠️ <b>No Tokens left today.</b>\n\n"
                f"Join our channel for <b>{DAILY_LIMIT_MEMBER} sessions/day</b> free!\n\n"
                f"💎 <b>Premium — {PREMIUM_PRICE} = {PREMIUM_TOKENS} Tokens</b>"
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("👉 Join Channel (Free)", url=CHANNEL_INVITE_URL),
            ], [
                InlineKeyboardButton(
                    f"💎 Buy Premium",
                    url=f"https://t.me/{BOT_USERNAME}?start=premium"
                ),
            ]])
        else:
            msg = (
                f"⚠️ <b>No Tokens left today.</b>\n\n"
                f"💎 <b>Premium — {PREMIUM_PRICE} = {PREMIUM_TOKENS} Tokens</b>"
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    f"💎 Buy Premium ",
                    url=f"https://t.me/{BOT_USERNAME}?start=premium"
                ),
            ]])
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=msg,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"[rar_next_prompt_callback] {e}")
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🟢 Easy",     callback_data="rar_level_easy"),
        InlineKeyboardButton("🟡 Medium",   callback_data="rar_level_medium"),
    ], [
        InlineKeyboardButton("🔴 Hard",     callback_data="rar_level_hard"),
        InlineKeyboardButton("🟣 Advanced", callback_data="rar_level_advanced"),
    ]])

    plan_label = "✅ Channel Member" if is_member else "👤 Guest"
    msg = (
        f"📚 <b>Read &amp; Record</b> 📚\n\n"
        f"{plan_label}  |  Tokens left today: <b>{remaining}/{daily_limit}</b>\n\n"
        f"Choose a difficulty level:"
    )
    try:
        await context.bot.send_message(chat_id=chat_id, text=msg,
                                       parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        print(f"[rar_next_prompt_callback] {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  /rarscore
# ══════════════════════════════════════════════════════════════════════════════
async def rar_score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user     = update.effective_user
        user_id  = user.id
        username = user.username or user.first_name or str(user_id)
        chat_id  = update.effective_chat.id

        stats       = _get_user_speech_stats(user_id, chat_id)
        rank        = _speech_rank(stats["avg_score"])
        is_member   = await _is_channel_member(context, user_id)
        today_count = _get_today_count(user_id)
        daily_limit = DAILY_LIMIT_MEMBER if is_member else DAILY_LIMIT_NON_MEMBER
        remaining   = max(0, daily_limit - today_count)

        msg = (
            f"🎙️ <b>YOUR SPEECH SCORE</b>\n"
            f"{'━' * 28}\n\n"
            f"👤  <b>{username}</b>\n\n"
            f"━━━ 🎤 <b>Read &amp; Record</b> ━━━\n"
            f"├ ⭐ Total Score    →  <b>{stats['total_score']} pts</b>\n"
            f"├ 🔁 Total Attempts →  <b>{stats['attempts']}</b>\n"
            f"├ 📊 Avg Score      →  <b>{stats['avg_score']}%</b>\n"
            f"└ 🏅 Rank           →  {rank}\n\n"
            f"━━━ 📅 <b>Today's Usage</b> ━━━\n"
            f"├ ✅ Used Today     →  <b>{today_count}/{daily_limit}</b>\n"
            f"├ 🔄 Remaining      →  <b>{remaining}</b>\n"
            f"└ 📋 Plan           →  {'✅ Channel Member' if is_member else '👤 Guest'}\n\n"
            f"<i>Use /record to practice!</i>"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("▶️ Start Practicing",
                                 callback_data="rar_next_prompt")
        ]])
        await _safe_reply(update, context, msg, reply_markup=keyboard)

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[rar_score_command] {e}")
    except Exception as e:
        print(f"[rar_score_command] Unexpected: {e}")



async def rar_leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id  = update.effective_chat.id
        df       = _load_speech_score_df()

        if df.empty:
            await _safe_reply(update, context, "📭 No scores yet. Be the first!")
            return

        group_df = df[df["chatid"] == chat_id].copy() if "chatid" in df.columns else df.copy()
        if group_df.empty:
            await _safe_reply(update, context, "📭 No scores in this group yet.")
            return

        group_df["avg"] = group_df["speechscore"] / group_df["attempts"].replace(0, 1)
        group_df = group_df.sort_values("speechscore", ascending=False).head(10)

        medals     = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        rank_title = ["Champion", "Runner Up", "2nd Runner Up"] + [""] * 7
        lines      = []

        for i, (_, row) in enumerate(group_df.iterrows()):
            name  = str(row.get("username", f"user_{int(row['userid'])}"))
            pts   = round(float(row["speechscore"]), 1)
            att   = int(row["attempts"])
            avg   = round(float(row["avg"]), 1)
            pos   = i + 1

            # score bar (5 blocks)
            filled   = round((avg / 100) * 5)
            bar      = "█" * filled + "░" * (5 - filled)

            # title line only for top 3
            title_line = f"  <i>{rank_title[i]}</i>\n" if rank_title[i] else ""

            lines.append(
                f"{medals[i]} <b>{pos}. {name}</b>\n"
                f"{title_line}"
                f"  ├ Score  : <b>{pts} pts</b>\n"
                f"  ├ Avg    : <b>{avg}%</b>  <code>{bar}</code>\n"
                f"  └ Tries  : <b>{att}</b>"
            )

        lb_text = (
            f"🏆 <b>SPEECH LEADERBOARD</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(lines) +
            f"\n\n━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Use /record to climb the ranks!</i>"
        )

        await _safe_reply(update, context, lb_text)

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[rar_leaderboard_command] {e}")
    except Exception as e:
        print(f"[rar_leaderboard_command] Unexpected: {e}")

async def my_speech_score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user     = update.effective_user
        user_id  = user.id
        username = user.username or user.first_name or str(user_id)
        chat_id  = update.effective_chat.id

        s    = _get_user_speech_stats(user_id, chat_id)
        rank = _speech_rank(s["avg_score"])
        info = await _get_user_limit_info(context, user_id)

        # ── most played level ──────────────────────────────────────────────
        levels  = ["easy", "medium", "hard", "advanced"]
        max_att = max(s[lvl]["attempts"] for lvl in levels)
        if max_att > 0:
            top_lvl   = max(levels, key=lambda l: s[l]["attempts"])
            top_icon  = LEVEL_COLORS.get(top_lvl, "📄")
            top_label = LEVEL_LABELS.get(top_lvl, top_lvl.capitalize())
            fav_line  = f"└ 🎯 Most Played  →  {top_icon} <b>{top_label}</b> ({max_att} attempts)\n"
        else:
            fav_line  = f"└ 🎯 Most Played  →  <i>No attempts yet</i>\n"
        header = "🎙️ <b>MY SPEECH SCORE</b>"
        # ── today section based on plan ────────────────────────────────────
        if info["is_premium"]:
            header = "💎 <b>PREMIUM MEMBER</b> 💎" 
            free_base = DAILY_LIMIT_MEMBER if info["is_member"] else DAILY_LIMIT_NON_MEMBER
            today_section = (
                f"━━━ 📅 <b>Today</b> ━━━\n"
                f"├ ✅ Free Used    →  <b>{info['today_count']}/{free_base}</b>\n"
                f"├ 🎟️ Tokens Left  →  <b>{info['tokens']}</b>\n"
                f"└ 🔄 Total Left   →  <b>{info['remaining']}</b>  💎 Premium\n"
            )
        else:
            today_section = (
                f"━━━ 📅 <b>Today</b> ━━━\n"
                f"├ ✅ Used        →  <b>{info['today_count']}/{info['daily_limit']}</b>\n"
                f"└ 🔄 Remaining   →  <b>{info['remaining']}</b>  "
                f"{'✅ Member' if info['is_member'] else '👤 Guest'}\n"
            )
        
        msg = (
            f"{header}\n"
            f"{'━' * 20}\n\n"
            f"👤  <b>{username}</b>\n\n"
            f"━━━ 🏆 <b>Overall</b> ━━━\n"
            f"├ ⭐ Total Points   →  <b>{s['total_score']}</b>\n"
            f"├ 🔁 Total Attempts →  <b>{s['attempts']}</b>\n"
            f"├ 📉 Avg Score      →  <b>{s['avg_score']}%</b>\n"
            f"├ 🏅 Rank           →  {rank}\n"
            f"{fav_line}\n"
            f"{today_section}\n"
            f"<i>Tap a level below to see your detailed score 👇</i>"
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🌱 Easy",     callback_data=f"mss_level_easy_{user_id}"),
            InlineKeyboardButton("📘 Medium",   callback_data=f"mss_level_medium_{user_id}"),
        ], [
            InlineKeyboardButton("🔥 Hard",     callback_data=f"mss_level_hard_{user_id}"),
            InlineKeyboardButton("💎 Advanced", callback_data=f"mss_level_advanced_{user_id}"),
        ], [
            InlineKeyboardButton("▶️ Start Practicing", callback_data="rar_next_prompt"),
        ]])

        await _safe_reply(update, context, msg, reply_markup=keyboard)

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[my_speech_score_command] {e}")
    except Exception as e:
        print(f"[my_speech_score_command] Unexpected: {e}")



async def mss_level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows detailed score for a specific level when button is tapped."""
    query   = update.callback_query
    chat_id = update.effective_chat.id
    user    = update.effective_user
    user_id = user.id

    try:
        await query.answer()
    except Exception:
        pass

    # callback_data = "mss_level_easy_12345"
    parts = query.data.split("_")   # ["mss", "level", "easy", "12345"]
    if len(parts) < 4:
        return

    level          = parts[2]
    owner_id       = int(parts[3])

    # only the user who ran /myspeechscore can tap their own buttons
    if user_id != owner_id:
        try:
            await query.answer("❌ This is not your score card!", show_alert=True)
        except Exception:
            pass
        return

    if level not in LEVEL_LABELS:
        return

    s         = _get_user_speech_stats(user_id, chat_id)
    d         = s[level]
    username  = user.username or user.first_name or str(user_id)
    icon      = LEVEL_COLORS.get(level, "📄")
    label     = LEVEL_LABELS.get(level, level.capitalize())

    if d["attempts"] == 0:
        detail_msg = (
            f"{icon} <b>{label} — Score Details</b>\n"
            f"{'━' * 20}\n\n"
            f"👤 <b>{username}</b>\n\n"
            f"<i>No attempts in this level yet.</i>\n\n"
        )
    else:
        # score bar visual
        avg   = d["avg"]
        filled = int(avg / 10)
        bar    = "🟩" * filled + "⬜" * (10 - filled)

        if avg >= 90:   grade = "🌟 Excellent"
        elif avg >= 75: grade = "✅ Great"
        elif avg >= 60: grade = "👍 Good"
        elif avg >= 45: grade = "📈 Developing"
        else:           grade = "🌱 Beginner"

        detail_msg = (
            f"{icon} <b>{label} — Score Details</b>\n"
            f"{'━' * 20}\n\n"
            f"👤 <b>{username}</b>\n\n"
            f"📊 <b>Performance</b>\n"
            f"├ 🔁 Attempts     →  <b>{d['attempts']}</b>\n"
            f"├ ⭐ Total Points  →  <b>{d['total']}</b>\n"
            f"├ 📉 Avg Score    →  <b>{avg}%</b>\n"
            f"├ 🏆 Best Score   →  <b>{d['best']}%</b>\n"
            f"└ 🎖️ Grade        →  {grade}\n\n"
            f"📈 <b>Score Bar</b>\n"
            f"{bar}  <b>{avg}%</b>\n\n"
            f"<i>Keep practicing to improve! 💪</i>"
        )

    # back button
    back_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Back to Overview",
                             callback_data=f"mss_back_{user_id}")
    ]])

    try:
        await query.edit_message_text(detail_msg, parse_mode="HTML",
                                      reply_markup=back_keyboard)
    except Exception:
        try:
            await context.bot.send_message(chat_id=chat_id, text=detail_msg,
                                           parse_mode="HTML",
                                           reply_markup=back_keyboard)
        except Exception as e:
            print(f"[mss_level_callback] {e}")


async def mss_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Back button → go back to overview."""
    query   = update.callback_query
    chat_id = update.effective_chat.id
    user    = update.effective_user
    user_id = user.id

    try:
        await query.answer()
    except Exception:
        pass

    owner_id = int(query.data.split("_")[-1])
    if user_id != owner_id:
        try:
            await query.answer("❌ This is not your score card!", show_alert=True)
        except Exception:
            pass
        return

    # rebuild overview
    username    = user.username or user.first_name or str(user_id)
    s           = _get_user_speech_stats(user_id, chat_id)
    rank        = _speech_rank(s["avg_score"])
    is_member   = await _is_channel_member(context, user_id)
    today_count = _get_today_count(user_id)
    daily_limit = DAILY_LIMIT_MEMBER if is_member else DAILY_LIMIT_NON_MEMBER
    remaining   = max(0, daily_limit - today_count)

    levels  = ["easy", "medium", "hard", "advanced"]
    max_att = max(s[lvl]["attempts"] for lvl in levels)
    if max_att > 0:
        top_lvl   = max(levels, key=lambda l: s[l]["attempts"])
        top_icon  = LEVEL_COLORS.get(top_lvl, "📄")
        top_label = LEVEL_LABELS.get(top_lvl, top_lvl.capitalize())
        fav_line  = f"└ 🎯 Most Played     →  {top_icon} <b>{top_label}</b> ({max_att} attempts)\n"
    else:
        fav_line  = f"└ 🎯 Most Played     →  <i>No attempts yet</i>\n"

    msg = (
        f"🎙️ <b>MY SPEECH SCORE</b>\n"
        f"{'━' * 20}\n\n"
        f"👤  <b>{username}</b>\n\n"
        f"━━━ 🏆 <b>Overall</b> ━━━\n"
        f"├ ⭐ Total Points   →  <b>{s['total_score']}</b>\n"
        f"├ 🔁 Total Attempts →  <b>{s['attempts']}</b>\n"
        f"├ 📉 Avg Score      →  <b>{s['avg_score']}%</b>\n"
        f"├ 🏅 Rank           →  {rank}\n"
        f"{fav_line}\n"
        f"━━━ 📅 <b>Today</b> ━━━\n"
        f"├ ✅ Used       →  <b>{today_count}/{daily_limit}</b>\n"
        f"└ 🔄 Remaining  →  <b>{remaining}</b>  "
        f"{'✅ Member' if is_member else '👤 Guest'}\n\n"
        f"<i>Tap a level below to see your detailed score 👇</i>"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🌱 Easy",     callback_data=f"mss_level_easy_{user_id}"),
        InlineKeyboardButton("📘 Medium",   callback_data=f"mss_level_medium_{user_id}"),
    ], [
        InlineKeyboardButton("🔥 Hard",     callback_data=f"mss_level_hard_{user_id}"),
        InlineKeyboardButton("💎 Advanced", callback_data=f"mss_level_advanced_{user_id}"),
    ], [
        InlineKeyboardButton("▶️ Start Practicing", callback_data="rar_next_prompt"),
    ]])

    try:
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        print(f"[mss_back_callback] {e}")

