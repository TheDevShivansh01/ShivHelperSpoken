import asyncio
import re,os
import random
import pandas as pd
from difflib import SequenceMatcher
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden, TimedOut
from Handlers.config import CONTRACTIONS
from Handlers.command import register_group
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.helpers import escape_markdown
from Handlers.voice import STREAK_EXCEL_PATH,_load_streak_df

EASY_FILEPATH = "UserScore/easytranslateSentences.xlsx"
MEDIUM_FILEPATH = "UserScore/mediumtranslateSentences.xlsx"
HARD_FILEPATH = "UserScore/hardtranslateSentences.xlsx"
COLUMNS = ["srno", "hindi", "english", "tense", "topic"]
GROUP_SEND_ID = -1002114430690
translation_game_state = {}
filepath = "UserScore/easytranslateSentences.xlsx"
comparisonScore =55
PRACTICE_SCORE_PATH = "UserScore/translationpracticescore.xlsx"

def _load_practice_df() -> pd.DataFrame:
    if os.path.exists(PRACTICE_SCORE_PATH):
        return pd.read_excel(PRACTICE_SCORE_PATH)
    os.makedirs(os.path.dirname(PRACTICE_SCORE_PATH), exist_ok=True)
    return pd.DataFrame(columns=['srno', 'userid', 'chatid', 'practicescore'])

def _increment_practice_score(user_id: int, chat_id: int):
    df   = _load_practice_df()
    mask = (df['userid'] == user_id) & (df['chatid'] == chat_id)

    if mask.any():
        df.loc[mask, 'practicescore'] += 1
    else:
        new_row = {
            'srno'         : int(df['srno'].max()) + 1 if not df.empty else 1,
            'userid'       : user_id,
            'chatid'       : chat_id,
            'practicescore': 1,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_excel(PRACTICE_SCORE_PATH, index=False)

async def adddata_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat.id

        # ✅ Only allowed in GROUP_SEND_ID
        if chat_id != GROUP_SEND_ID:
            await update.message.reply_text("❌ This command is not allowed here.")
            return

        # ✅ Must be a reply to a message
        if not update.message.reply_to_message:
            await update.message.reply_text(
                "❌ Please reply to a .txt file containing the data.\n"
                "Format per line: `srno~hindi~english~tense~topic`",
                parse_mode="Markdown"
            )
            return

        # ✅ Must provide difficulty argument
        args = context.args
        if not args or args[0].lower() not in ["easy", "medium", "hard"]:
            await update.message.reply_text(
                "❌ Please specify difficulty.\n"
                "Usage: `/adddata easy` or `/adddata medium` or `/adddata hard`",
                parse_mode="Markdown"
            )
            return

        difficulty = args[0].lower()
        if difficulty == "easy":
            filepath = EASY_FILEPATH
        elif difficulty == "medium":
            filepath = MEDIUM_FILEPATH
        else:
            filepath = HARD_FILEPATH

        # ✅ Get the .txt file from replied message
        replied = update.message.reply_to_message
        if not replied.document:
            await update.message.reply_text(
                "❌ Please reply to a *.txt* file, not a text message.",
                parse_mode="Markdown"
            )
            return

        # ✅ Check it's actually a .txt file
        file_name = replied.document.file_name or ""
        if not file_name.lower().endswith(".txt"):
            await update.message.reply_text(
                "❌ Only *.txt* files are supported.",
                parse_mode="Markdown"
            )
            return

        # ✅ Download and read the file
        try:
            file = await context.bot.get_file(replied.document.file_id)
            file_bytes = await file.download_as_bytearray()
            raw_text = file_bytes.decode("utf-8").strip()
        except Exception as e:
            print(f"[adddata_command] File download failed: {e}")
            await update.message.reply_text("❌ Could not read the file. Please try again.")
            return

        # ✅ Parse lines
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        parsed_rows = []
        failed_lines = []

        for line in lines:
            parts = line.split("~")
            if len(parts) != 5:
                failed_lines.append(line)
                continue
            try:
                row = {
                    "srno":    0,  # will be reassigned below
                    "hindi":   parts[1].strip(),
                    "english": parts[2].strip(),
                    "tense":   parts[3].strip(),
                    "topic":   parts[4].strip(),
                }
                parsed_rows.append(row)
            except ValueError:
                failed_lines.append(line)
                continue

        if not parsed_rows:
            await update.message.reply_text(
                "❌ No valid rows found.\n"
                "Each line must be: `srno~hindi~english~tense~topic`",
                parse_mode="Markdown"
            )
            return

        # ✅ Load existing Excel or create new one
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if os.path.exists(filepath):
            df = pd.read_excel(filepath)
            df.columns = [c.strip().lower() for c in df.columns]
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""
        else:
            df = pd.DataFrame(columns=COLUMNS)

        # ✅ Continue srno from last existing srno
        if df.empty or len(df) == 0:
            last_srno = 0
        else:
            last_srno = int(df["srno"].max())

        # ✅ Assign new srno starting from last_srno + 1
        new_df = pd.DataFrame(parsed_rows)
        new_df = new_df.reset_index(drop=True)
        new_df["srno"] = range(last_srno + 1, last_srno + 1 + len(new_df))

        df = pd.concat([df, new_df], ignore_index=True).sort_values("srno").reset_index(drop=True)
        df.to_excel(filepath, index=False)

        # ✅ Build result message
        result_msg = (
            f"✅ *Data added successfully!* ({difficulty.capitalize()})\n\n"
            f"• Added: *{len(new_df)}* rows\n"
            f"• Srno range: *{last_srno + 1}* to *{last_srno + len(new_df)}*\n"
        )
        if failed_lines:
            result_msg += f"• Invalid format: *{len(failed_lines)}* lines\n"
            result_msg += "\n*Invalid lines:*\n" + "\n".join(f"`{l}`" for l in failed_lines[:5])

        await update.message.reply_text(result_msg, parse_mode="Markdown")

        # ✅ Send updated Excel file back to group
        with open(filepath, "rb") as f:
            await context.bot.send_document(
                chat_id=GROUP_SEND_ID,
                document=f,
                filename=os.path.basename(filepath),
                caption=f"📊 Updated *{difficulty.capitalize()}* sentences file.",
                parse_mode="Markdown"
            )

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[adddata_command] {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")
    except Exception as e:
        print(f"[adddata_command] Unexpected: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")


def load_sentences(filepath: str) -> pd.DataFrame:
    """Load excel file with columns: srno, hindi, english"""
    df = pd.read_excel(filepath)
    df.columns = [c.strip().lower() for c in df.columns]
    # Expected columns: srno, hindi, english
    return df.reset_index(drop=True)
 
# Load once at startup — adjust path as needed
try:
    SENTENCES_DF = load_sentences(filepath)
except Exception as e:
    print(f"[WARNING] Could not load sentences.xlsx: {e}")
    SENTENCES_DF = pd.DataFrame(columns=["srno", "hindi", "english"])

def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)   # remove punctuation
    text = re.sub(r"\s+", " ", text)
    return text
 
def expand_contractions(text: str) -> str:
    """Replace contracted forms with expanded forms."""
    for expanded, contracted in CONTRACTIONS.items():
        text = text.replace(contracted, expanded)
    return text
 
def normalize_all(text: str) -> str:
    """Full normalization: expand contractions → normalize."""
    text = normalize_text(text)
    text = expand_contractions(text)
    return normalize_text(text)  # normalize again after expansion
 
def word_match_score(user_text: str, correct_text: str) -> float:
    user_words = user_text.split()
    correct_words = correct_text.split()

    if not correct_words:
        return 0.0

    # ── Jaccard (which words match) ──
    user_set = set(user_words)
    correct_set = set(correct_words)
    intersection = user_set & correct_set
    union = user_set | correct_set
    jaccard = len(intersection) / len(union)

    # ── Position score (are matched words in the right place?) ──
    min_len = min(len(user_words), len(correct_words))
    max_len = max(len(user_words), len(correct_words))
    position_matches = sum(
        1 for i in range(min_len) if user_words[i] == correct_words[i]
    )
    position_score = position_matches / max_len

    # ── 50% jaccard + 50% position ──
    return (jaccard * 0.50) + (position_score * 0.50)


def letter_match_score(user_text: str, correct_text: str) -> float:
    """
    Character-level similarity using SequenceMatcher.
    Catches partial/misspelled words.
    """
    return SequenceMatcher(None, user_text, correct_text).ratio()
 
def calculate_match_percentage(user_answer: str, correct_answer: str) -> float:
    u = normalize_all(user_answer)
    c = normalize_all(correct_answer)

    if u == c:
        return 100.0

    word_score = word_match_score(u, c)
    letter_score = letter_match_score(u, c)
    combined = (word_score * 0.70 + letter_score * 0.30) * 100
    return round(combined, 1)

 
INACTIVITY_SECONDS = 10 * 60  
 
async def inactivity_reset(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Called after 30 min of inactivity. Resets state and notifies group."""
    await asyncio.sleep(INACTIVITY_SECONDS)
    if chat_id in translation_game_state:
        del translation_game_state[chat_id]
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⏰ The previous translation game was canceled due to 30 minutes of inactivity.\n"
                "You can start a new one with /starttranslation"
            )
        )
    except Exception as e:
        print(f"[inactivity_reset] Could not send message to {chat_id}: {e}")
 
def reset_inactivity_timer(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Cancel existing timer and start a fresh 30-min countdown."""
    state = translation_game_state.get(chat_id)
    if not state:
        return
    old_task = state.get("timeout_task")
    if old_task and not old_task.done():
        old_task.cancel()
    task = asyncio.create_task(inactivity_reset(chat_id, context))
    state["timeout_task"] = task
 
 

async def send_sentence(chat_id: int, context: ContextTypes.DEFAULT_TYPE, srno: int):
    state = translation_game_state.get(chat_id)
    if not state:
        return False

    df = state["df"]
    row = df[df["srno"] == srno]

    if row.empty:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ No more sentences! Game over.\nUse /starttranslation to play again."
        )
        _cleanup_state(chat_id)
        return False

    hindi = str(row.iloc[0]["hindi"]).strip()
    english = str(row.iloc[0]["english"]).strip()

    # ✅ Show previous correct answer before loading new sentence
    prev_english = state.get("current_english", "")
    

    state["current_srno"] = srno
    state["current_hindi"] = hindi
    state["current_english"] = english
    state["answered_users"] = set()

    label = "🟢 Easy" 

    if state["difficulty"] == "easy":
        label = "🟢 Easy"
    elif state["difficulty"] == "medium":
        label = "🟡 Medium"
    else:
        label = "🔴 Hard"
    

    safe_hindi = escape_markdown(hindi, version=2)
    safe_prev = escape_markdown(prev_english or "", version=2)
    safe_label = escape_markdown(label, version=2)

    if prev_english:
        await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"📖 *Correct answer:* _{safe_prev}_\n\n"
            f"🌐 *Translate Next Sentence:*\n\n"
            f"*Level:* {safe_label}\n\n"
            f"🇮🇳 *{safe_hindi}*\n\n"
        ),
        parse_mode="MarkdownV2"
    )
    else:
        await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🌐 *Translate this sentence into English:*\n\n"
            f"*Level:* {safe_label}\n\n"
            f"🇮🇳 *{safe_hindi}*\n\n"
        ),
        parse_mode="MarkdownV2"
    )
    return True


def _cleanup_state(chat_id: int):
    """Cancel timer and remove state."""
    state = translation_game_state.pop(chat_id, None)
    if state:
        task = state.get("timeout_task")
        if task and not task.done():
            task.cancel()
 
 
async def start_translation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat.id

        if chat_id in translation_game_state:
            try:
                await update.message.reply_text(
                "⚠️ A translation game is already running here.\n"
                "Use /next to continue or /cancel to stop."
               )
            except Exception as ex:
                await context.bot.send_message (chat_id=chat_id,
        text=(
            "⚠️ A translation game is already running here.\n"
            "Use /next to continue or /cancel to stop."
        ))
            return

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🟢 Easy", callback_data="tg_diff_easy"),
            InlineKeyboardButton("🟡 Medium", callback_data="tg_diff_medium"),
            InlineKeyboardButton("🔴 Hard", callback_data="tg_diff_hard"),
        ]])

        try:
            await update.message.reply_text("🎮 *Welcome to the Translation Game!*\n\nSelect difficulty to begin:",reply_markup=keyboard,parse_mode="Markdown")
        except Exception as ex:
            await context.bot.send_message(chat_id=chat_id,text="🎮 *Welcome to the Translation Game!*\n\nSelect difficulty to begin:",reply_markup=keyboard,parse_mode="Markdown")

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[start_translation_command] {e}")

async def difficulty_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id

    if chat_id in translation_game_state:
        try:
            await query.edit_message_text("⚠️ A game is already running here.")
        except Exception as ex:
            await context.bot.send_message(chat_id=chat_id,text="⚠️ A game is already running here.")   
        return

    if query.data == "tg_diff_easy":
        difficulty = "easy"
        filepath = EASY_FILEPATH
    elif query.data == "tg_diff_medium":   
        difficulty = "medium"
        filepath = MEDIUM_FILEPATH
    else:
        difficulty = "hard"
        filepath = HARD_FILEPATH

    try:
        df = load_sentences(filepath)
    except Exception as e:
        print(f"[difficulty_callback] Failed to load {filepath}: {e}")  # log for developer
        try:
            await query.edit_message_text("❌ Something went wrong. Please try again later." )
        except Exception:
            await context.bot.send_message(chat_id=chat_id,text="❌ Something went wrong. Please try again later." )
        return
        
    if df.empty:
        try:
            await query.edit_message_text("❌ Sentences file is empty!")
        except Exception:
            await context.bot.send_message(chat_id=chat_id,text="❌ Sentences file is empty!" )
          
        return

    random_idx = random.randint(0, len(df) - 1)
    first_srno = int(df.iloc[random_idx]["srno"])

    translation_game_state[chat_id] = {
        "is_active": True,
        "difficulty": difficulty,
        "df": df,
        "current_srno": None,
        "current_hindi": None,
        "current_english": None,
        "answered_users": set(),
        "scores": {},
        "timeout_task": None,
        "used_srnos": {first_srno},
    }

    if difficulty == "easy":
        label = "🟢 Easy"
    elif difficulty == "medium":
        label = "🟡 Medium"
    else:
        label = "🔴 Hard"

    msg_text = (
        f"🎮 *Translation Game Started!* {label}\n\n"
        f"• Translate each Hindi sentence into English\n"
        f"• Score ≥55% → your result will be shown\n"
        f"• Score ≥90% → next sentence loads automatically\n"
        f"• Use /next to move on manually\n"
    )

    # ✅ Try edit, fallback to send_message
    try:
        await query.edit_message_text(msg_text, parse_mode="Markdown")
    except Exception as ex:
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            parse_mode="Markdown"
        )

    await send_sentence(chat_id, context, first_srno)
    reset_inactivity_timer(chat_id, context)
# ─────────────────────────────────────────────
 
async def next_sentence_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat.id

        if chat_id not in translation_game_state:
            try:
                await update.message.reply_text("❌ No translation game is running. Use /starttranslation to begin.")
            except Exception as ex:
                await context.bot.send_message(chat_id=chat_id,text="❌ No translation game is running. Use /starttranslation to begin.")
            return

        state = translation_game_state[chat_id]
        df = state["df"]
        used = state.get("used_srnos", set())

        # All srno values not yet used
        all_srnos = set(df["srno"].tolist())
        remaining = list(all_srnos - used)

        if not remaining:
            try:
                await update.message.reply_text( "🏁 All sentences completed! Game over.\n" "Use /starttranslation to play again.")
            except Exception as ex:
                await context.bot.send_message(chat_id=chat_id,text="🏁 All sentences completed! Game over.\n" "Use /starttranslation to play again.")
            _cleanup_state(chat_id)
            return

        next_srno = random.choice(remaining)
        state["used_srnos"].add(next_srno)
        
       

        await send_sentence(chat_id, context, next_srno)
        reset_inactivity_timer(chat_id, context)

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[next_sentence_command] {e}")

 
async def translation_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Listens to all messages in the group.
    Only processes if:
      - translation game is active for this chat
      - message has more than 2 words
      - user hasn't already scored ≥75% this round
    """
    try:
        if not update.message or not update.message.text:
            return
 
        chat_id = update.message.chat.id

        await register_group(update, context)
        if chat_id not in translation_game_state:
            return
 
        state = translation_game_state[chat_id]
        if not state.get("is_active"):
            return
 
        user = update.message.from_user
        user_id = user.id
        user_name = user.first_name or user.username or str(user_id)
        message_text = update.message.text.strip()
 
        # Ignore commands
        if message_text.startswith("/"):
            return
 
        # Must have more than 2 words
        words = message_text.split()
        if len(words) <= 2:
            return
 
        correct_english = state.get("current_english", "")
        if not correct_english:
            return
 
        # Calculate match
        score = calculate_match_percentage(message_text, correct_english)
 
        if score >= 55:
            state["answered_users"].add(user_id)
 
            
            if user_id not in state["scores"]:
                state["scores"][user_id] = {"name": user_name, "total": 0.0, "rounds": 0}
            state["scores"][user_id]["total"] += score
            state["scores"][user_id]["rounds"] += 1
 
            # Reply with result
            try: 
                await update.message.reply_text(
                f"✅ *{user_name}*, you scored *{score}%*! {'🎉 Excellent!' if score >= 90 else '👍 Good job!'}",
                parse_mode="Markdown"
                )
            except Exception as ex:
                await context.bot.send_message(chat_id=chat_id,text=f"✅ *{user_name}*, you scored *{score}%*! {'🎉 Excellent!' if score >= 90 else '👍 Good job!'}",
                parse_mode="Markdown")
 
            # Auto-advance if score ≥ 90%
            if score >= 90:
                _increment_practice_score(user_id, chat_id)
                await asyncio.sleep(1.5)   # small pause so result is visible
                await _auto_next_sentence(chat_id, context, state)

        # Reset inactivity timer on any valid attempt
        reset_inactivity_timer(chat_id, context)
 
    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[translation_message_handler] {e}")
    except Exception as e:
        print(f"[translation_message_handler] Unexpected: {e}")
 
async def _auto_next_sentence(chat_id: int, context: ContextTypes.DEFAULT_TYPE, state: dict):
    df = state["df"]
    used = state.get("used_srnos", set())

    all_srnos = set(df["srno"].tolist())
    remaining = list(all_srnos - used)

    if not remaining:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🏁 *All sentences completed! Game over.*\nUse /starttranslation to play again.",
            parse_mode="Markdown"
        )
        _cleanup_state(chat_id)
        return

    next_srno = random.choice(remaining)
    state["used_srnos"].add(next_srno)

    await send_sentence(chat_id, context, next_srno)
    reset_inactivity_timer(chat_id, context)

async def cancel_translation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat.id

        if chat_id not in translation_game_state:
            await update.message.reply_text(
                "❌ No translation game is running here."
            )
            return

        state = translation_game_state[chat_id]
        correct_english = state.get("current_english", "")

        _cleanup_state(chat_id)
        try:
            await update.message.reply_text(
            f"🛑 *Translation game has been canceled!*\n\n"
            f"📖 *Last correct answer was:*\n_{correct_english}_\n\n"
            f"Use /starttranslation to start a new game.",
            parse_mode="Markdown"
            )
        except Exception as ex:
            await context.bot.sendMessage(chat_id=chat_id,text= f"🛑 *Translation game has been canceled!*\n\n"
            f"📖 *Last correct answer was:*\n_{correct_english}_\n\n"
            f"Use /starttranslation to start a new game.",
            parse_mode="Markdown")


    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[cancel_translation_command] {e}")

async def mystreak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    user_id  = user.id
    username = user.username or user.first_name or f"user_{user_id}"
    chat_id  = update.effective_chat.id

    # ── Load ReadAloud streak ──────────────────────────────────────────────────
    streak_data = {
        'current_streak': 0, 'max_streak': 0,
        'streak7_count': 0,  'streak30_count': 0
    }
    if os.path.exists(STREAK_EXCEL_PATH):
        df   = _load_streak_df()
        mask = df['user_id'] == user_id
        if mask.any():
            row = df[mask].iloc[0]
            streak_data = {
                'current_streak' : int(row['current_streak']),
                'max_streak'     : int(row['max_streak']),
                'streak7_count'  : int(row['streak7_count']),
                'streak30_count' : int(row['streak30_count']),
            }

    # ── Load Translation practice score ───────────────────────────────────────
    practice_score = 0
    if os.path.exists(PRACTICE_SCORE_PATH):
        pdf  = pd.read_excel(PRACTICE_SCORE_PATH)
        mask = (pdf['userid'] == user_id) & (pdf['chatid'] == chat_id)
        if mask.any():
            practice_score = int(pdf[mask].iloc[0]['practicescore'])

    # ── Build badge visuals ────────────────────────────────────────────────────
    cs       = streak_data['current_streak']
    ms       = streak_data['max_streak']
    s7       = streak_data['streak7_count']
    s30      = streak_data['streak30_count']

    # Streak fire badge
    if cs == 0:
        streak_badge = "❄️ No active streak"
    elif cs < 7:
        streak_badge = "🔥" * cs
    elif cs < 30:
        streak_badge = f"🔥×{cs}"
    else:
        streak_badge = f"🌋 LEGENDARY ×{cs}"

    # Translation rank
    if practice_score == 0:
        trans_rank = "🌱 Beginner"
    elif practice_score < 10:
        trans_rank = "📘 Learner"
    elif practice_score < 25:
        trans_rank = "📗 Intermediate"
    elif practice_score < 50:
        trans_rank = "📙 Advanced"
    elif practice_score < 100:
        trans_rank = "🏅 Expert"
    else:
        trans_rank = "👑 Master"

    # Week/Month badge display
    week_badges  = "🏆" * min(s7, 10)  + (f" ×{s7}" if s7 > 10 else "") if s7 else "—"
    month_badges = "🥇" * min(s30, 5)  + (f" ×{s30}" if s30 > 5 else "") if s30 else "—"

    message = (
    f"🏅 <b>PLAYER STATS</b>\n"
    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
    f"👤  <b>{username}</b>\n\n"

     f"━━━ 🎙️ <b>Read Aloud</b> ━━━\n"
    f"├ 🔥 Streak Today   →  <b>{cs} day(s)</b>\n"
    f"├ 🏁 Personal Best  →  <b>{ms} day(s)</b>\n"
    f"├ 🏆 Week Badges    →  {week_badges}\n"
    f"└ 🥇 Month Badges   →  {month_badges}\n\n"

    f"━━━ 🌐 <b>Translation</b> ━━━\n"
    f"├ ⭐ Practice Points →  <b>{practice_score} pts</b>\n"
    f"└ 🎖️ Current Rank    →  {trans_rank}\n\n"

    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
    f"{streak_badge}\n"
    f"<i>Keep showing up. Every day counts. 💪</i>"
)
    try:
        await update.message.reply_text(message, parse_mode="HTML")
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")