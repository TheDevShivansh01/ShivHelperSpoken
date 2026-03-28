import asyncio
import os
import random
import pandas as pd
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden, TimedOut
from telegram.helpers import escape_markdown


WORD_EXCEL_PATH     = "Data/daily_words_v2.xlsx"        
WORD_SCORE_PATH     = "UserScore/wordgamescore.xlsx"      
WORD_INACTIVITY_SEC = 10 * 60                       

word_game_state: dict = {}


def _load_word_df() -> pd.DataFrame:
    if not os.path.exists(WORD_EXCEL_PATH):
        raise FileNotFoundError(f"Words file not found: {WORD_EXCEL_PATH}")
    df = pd.read_excel(WORD_EXCEL_PATH)
    df.columns = [c.strip().lower() for c in df.columns]
    return df.reset_index(drop=True)


def _load_score_df() -> pd.DataFrame:
    if os.path.exists(WORD_SCORE_PATH):
        return pd.read_excel(WORD_SCORE_PATH)
    os.makedirs(os.path.dirname(WORD_SCORE_PATH), exist_ok=True)
    return pd.DataFrame(columns=["srno", "userid", "chatid", "wordscore"])


def _increment_word_score(user_id: int, chat_id: int):
    df   = _load_score_df()
    mask = (df["userid"] == user_id) & (df["chatid"] == chat_id)
    if mask.any():
        df.loc[mask, "wordscore"] += 1
    else:
        new_row = {
            "srno"     : int(df["srno"].max()) + 1 if not df.empty else 1,
            "userid"   : user_id,
            "chatid"   : chat_id,
            "wordscore": 1,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(WORD_SCORE_PATH, index=False)


def _get_word_score(user_id: int, chat_id: int) -> int:
    if not os.path.exists(WORD_SCORE_PATH):
        return 0
    df   = pd.read_excel(WORD_SCORE_PATH)
    mask = (df["userid"] == user_id) & (df["chatid"] == chat_id)
    if mask.any():
        return int(df[mask].iloc[0]["wordscore"])
    return 0


def _build_hint(english_word: str) -> str:
    if not english_word:
        return ""
    letters = [english_word[0]] + ["_"] * (len(english_word) - 1)
    return " ".join(letters)


async def _inactivity_reset(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(WORD_INACTIVITY_SEC)
    if chat_id in word_game_state:
        _cleanup_word_state(chat_id)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⏰ Word game was canceled due to 10 minutes of inactivity.\n"
                "Use /getword to start a new game!"
            )
        )
    except Exception as e:
        print(f"[_inactivity_reset] {e}")


def _reset_inactivity_timer(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    state = word_game_state.get(chat_id)
    if not state:
        return
    old = state.get("timeout_task")
    if old and not old.done():
        old.cancel()
    state["timeout_task"] = asyncio.create_task(_inactivity_reset(chat_id, context))


def _cleanup_word_state(chat_id: int):
    state = word_game_state.pop(chat_id, None)
    if state:
        task = state.get("timeout_task")
        if task and not task.done():
            task.cancel()


def _build_scoreboard(state: dict) -> str:
    """Final scoreboard: topper first, shows correct + passed counts."""
    scores   = state.get("scores", {})     # uid → {name, count}
    passed   = state.get("pass_users", {}) # uid → {name, count}
    total    = state.get("word_count", 0)
    category = state.get("category", "")

    # Merge all participants
    all_users: dict = {}
    for uid, data in scores.items():
        all_users[uid] = {
            "name"   : data["name"],
            "correct": data["count"],
            "passed" : passed.get(uid, {}).get("count", 0),
        }
    for uid, pdata in passed.items():
        if uid not in all_users:
            all_users[uid] = {
                "name"   : pdata["name"],
                "correct": 0,
                "passed" : pdata["count"],
            }

    if not all_users:
        return (
            f"🏁 <b>GAME OVER!</b>\n"
            f"📂 Category: <b>{category}</b>  |  Words played: <b>{total}</b>\n\n"
            f"📊 No one participated this round!"
        )

    # Sort: most correct first
    sorted_users = sorted(
        all_users.items(),
        key=lambda x: x[1]["correct"],
        reverse=True
    )

    medals = ["🥇", "🥈", "🥉"]
    lines  = [
        f"🏁 <b>GAME OVER!</b>",
        f"📂 Category: <b>{category}</b>  |  Words played: <b>{total}</b>",
        f"",
        f"📊 <b>SCOREBOARD</b> (Top 10)",
        f"━━━━━━━━━━━━━━━━━",
    ]

    for i, (uid, data) in enumerate(sorted_users[:10]):
        medal = medals[i] if i < 3 else f"#{i + 1}"
        lines.append(
            f"{medal} <b>{data['name']}</b>  "
            f"✅ {data['correct']} correct  |  ⏭️ {data['passed']} passed"
        )

    lines += [
        "━━━━━━━━━━━━━━━━━",
        "<i>Thanks for playing! Use /getword to play again.</i>",
    ]
    return "\n".join(lines)

async def _send_word(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    prev_english: str = "",
    guesser_name: str = "",   # "" means it was passed/skipped
):
    state = word_game_state.get(chat_id)
    if not state:
        return

    df        = state["df"]
    used      = state.get("used_srnos", set())
    all_srnos = set(df["srno"].tolist())
    remaining = list(all_srnos - used)
    word_count = state.get("word_count", 0)
    max_words  = state.get("max_words", 10)

    if word_count >= max_words:
        board = _build_scoreboard(state)
        _cleanup_word_state(chat_id)
        try:
            await context.bot.send_message(chat_id=chat_id, text=board, parse_mode="HTML")
        except Exception as e:
            print(f"[_send_word] scoreboard send failed: {e}")
        return

    if not remaining:
        board = _build_scoreboard(state)
        _cleanup_word_state(chat_id)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="📭 <b>No more words in this category!</b>\n\n" + board,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[_send_word] {e}")
        return

    next_srno = random.choice(remaining)
    state["used_srnos"].add(next_srno)
    state["word_count"] = word_count + 1

    row          = df[df["srno"] == next_srno].iloc[0]
    hindi_word   = str(row["hindiword"]).strip()
    english_word = str(row["englishword"]).strip()
    category     = str(row["code"]).strip()

    state["current_srno"]    = next_srno
    state["current_hindi"]   = hindi_word
    state["current_english"] = english_word
    state["answered_users"]  = set()

    hint        = _build_hint(english_word)
    current_num = state["word_count"]

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭️ Pass", callback_data="wg_next")
    ]])

    lines = []

    if prev_english:
        if guesser_name:
            lines.append(f"✅ <b>{guesser_name}</b> guessed the word: <b>{prev_english}</b>")
        else:
            lines.append(f"⏭️ Word passed! Answer was: <b>{prev_english}</b>")
        lines.append("")

    lines += [
        f"🃏 <b>Word {current_num}/{max_words}</b>  |  📂 <b>{category}</b>",
        f"",
        f"🇮🇳 Hindi: <b>{hindi_word}</b>",
        f"💡 Hint: <code>{hint}</code>",
    ]

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="\n".join(lines),
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"[_send_word] send failed: {e}")


async def getword_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat.id

        if chat_id in word_game_state:
            await update.message.reply_text(
                "⚠️ A word game is already running here.\n"
                "Use /stopword to stop it first."
            )
            return

        # Validate file exists
        try:
            _load_word_df()
        except FileNotFoundError:
            await update.message.reply_text(
                "❌ Words file not found. Please ensure `UserScore/words.xlsx` exists."
            )
            return

        # Ask how many words
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("10",  callback_data="wg_count_10"),
                InlineKeyboardButton("20",  callback_data="wg_count_20"),
                InlineKeyboardButton("30",  callback_data="wg_count_30"),
            ],
            [
                InlineKeyboardButton("40",  callback_data="wg_count_40"),
                InlineKeyboardButton("50",  callback_data="wg_count_50"),
            ],
        ])

        await update.message.reply_text(
            "🎮 <b>Word Game!</b>\n\nHow many words do you want to play?",
            parse_mode="HTML",
            reply_markup=keyboard
        )

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[getword_command] {e}")
    except Exception as e:
        print(f"[getword_command] Unexpected: {e}")



async def wordgame_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    data    = query.data

    if data.startswith("wg_count_"):
        if chat_id in word_game_state:
            try:
                await query.edit_message_text("⚠️ A game is already running here.")
            except Exception:
                pass
            return

        max_words = int(data.split("_")[-1])

        try:
            df = _load_word_df()
        except FileNotFoundError:
            try:
                await query.edit_message_text("❌ Words file not found.")
            except Exception:
                pass
            return

        if df.empty:
            try:
                await query.edit_message_text("❌ Words file is empty!")
            except Exception:
                pass
            return

        # Pick a random category then filter
        all_codes   = df["code"].dropna().unique().tolist()
        chosen_code = random.choice(all_codes)
        cat_df      = df[df["code"] == chosen_code].reset_index(drop=True)

        if cat_df.empty:
            try:
                await query.edit_message_text("❌ No words found for the selected category.")
            except Exception:
                pass
            return

        word_game_state[chat_id] = {
            "is_active"      : True,
            "df"             : cat_df,
            "category"       : chosen_code,
            "max_words"      : max_words,
            "word_count"     : 0,
            "current_srno"   : None,
            "current_hindi"  : None,
            "current_english": None,
            "answered_users" : set(),
            "scores"         : {},   # uid → {name, count}
            "pass_users"     : {},   # uid → {name, count}
            "used_srnos"     : set(),
            "timeout_task"   : None,
        }

        intro = (
            f"🎮 <b>Word Game Started!</b>\n\n"
            f"📂 Category: <b>{chosen_code}</b>\n"
            f"🔢 Words to play: <b>{max_words}</b>\n\n"
            f"• Type the English word for each Hindi clue\n"
            f"• First letter is shown as a hint\n"
            f"• Correct answer → next word loads automatically\n"
            f"• Tap ⏭️ <b>Pass</b> to skip a word\n"
            f"• Use /stopword to end early"
        )

        try:
            await query.edit_message_text(intro, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=intro, parse_mode="HTML")

        await _send_word(chat_id, context)
        _reset_inactivity_timer(chat_id, context)
        return

    if data == "wg_next":
        if chat_id not in word_game_state:
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ No word game is running. Use /getword to start."
            )
            return

        state        = word_game_state[chat_id]
        prev_english = state.get("current_english", "")

        # Track who passed
        puser    = update.effective_user
        puser_id = puser.id
        pname    = puser.first_name or puser.username or str(puser_id)

        if puser_id not in state["pass_users"]:
            state["pass_users"][puser_id] = {"name": pname, "count": 0}
        state["pass_users"][puser_id]["count"] += 1

        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        await _send_word(chat_id, context, prev_english=prev_english, guesser_name="")
        _reset_inactivity_timer(chat_id, context)



async def wordgame_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return

        chat_id = update.message.chat.id

        if chat_id not in word_game_state:
            return

        state = word_game_state[chat_id]
        if not state.get("is_active"):
            return

        user      = update.message.from_user
        user_id   = user.id
        user_name = user.first_name or user.username or str(user_id)
        msg_text  = update.message.text.strip()

        if msg_text.startswith("/"):
            return

        correct_english = state.get("current_english", "")
        if not correct_english:
            return

        # Case-insensitive exact match
        if msg_text.lower() != correct_english.lower():
            _reset_inactivity_timer(chat_id, context)
            return

        # Prevent double scoring on same word
        if user_id in state.get("answered_users", set()):
            return

        state["answered_users"].add(user_id)

        # Session score
        if user_id not in state["scores"]:
            state["scores"][user_id] = {"name": user_name, "count": 0}
        state["scores"][user_id]["count"] += 1

        # Persist to Excel
        _increment_word_score(user_id, chat_id)

        await asyncio.sleep(1.2)
        await _send_word(chat_id, context, prev_english=correct_english, guesser_name=user_name)
        _reset_inactivity_timer(chat_id, context)

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[wordgame_message_handler] {e}")
    except Exception as e:
        print(f"[wordgame_message_handler] Unexpected: {e}")


# ─────────────────────────────────────────────
# /stopword COMMAND
# ─────────────────────────────────────────────

async def stopword_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.message.chat.id

        if chat_id not in word_game_state:
            await update.message.reply_text("❌ No word game is running here.")
            return

        state = word_game_state[chat_id]
        board = _build_scoreboard(state)
        _cleanup_word_state(chat_id)

        try:
            await update.message.reply_text(
                f"🛑 <b>Word game stopped early!</b>\n\n{board}",
                parse_mode="HTML"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🛑 Word game stopped early!\n\n{board}",
                parse_mode="HTML"
            )

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[stopword_command] {e}")
    except Exception as e:
        print(f"[stopword_command] Unexpected: {e}")




async def mywordscore_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user      = update.effective_user
        user_id   = user.id
        user_name = user.username or user.first_name or f"user_{user_id}"
        chat_id   = update.effective_chat.id

        score = _get_word_score(user_id, chat_id)

        message = (
            f"🃏 <b>WORD GAME STATS</b>\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"👤 <b>{user_name}</b>\n\n"
            f"⭐ Total Words Correct → <b>{score} pts</b>\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"<i>Keep guessing. Every word counts! 💪</i>"
        )

        try:
            await update.message.reply_text(message, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[mywordscore_command] {e}")
    except Exception as e:
        print(f"[mywordscore_command] Unexpected: {e}")