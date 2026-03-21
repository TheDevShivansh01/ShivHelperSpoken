import os
import re
import asyncio
import random
import pandas as pd
from datetime import date, datetime
from difflib import SequenceMatcher
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden, TimedOut
from Handlers.utils import _safe_reply

READING_FILEPATH  = "Data/reading_paragraphs.xlsx"
PREMIUM_TOKEN_PATH = "UserScore/premium_tokens.xlsx"
SPEECH_SCORE_PATH = "UserScore/speechscore.xlsx"
QR_CODE_PATH       = "Data/payment.jpg" 
RAR_DAILY_PATH    = "UserScore/rar_daily_usage.xlsx"
NIMISH_CHAT_ID  = 8502504224



CHANNEL_ID = "-1002234035497"
CHANNEL_USERNAME   = "@currentaffairs_04"
CHANNEL_INVITE_URL = "https://t.me/currentaffairs_04"
PREMIUM_CONTACT    = "https://t.me/O000000000O00000000O"
BOT_MANAGEMENT_GROUP_ID = -1002359766306 # apna management group id daalo
PARA_MIN_WORDS = {
    "easy"    : 10,
    "medium"  : 30,
    "hard"    : 60,
    "advanced": 100,
}

PREMIUM_PRICE      = "₹10"
PREMIUM_TOKENS     = 50  # ← apna QR image yahan rakho
BOT_USERNAME       = "Tesingt_04bot"
addpara_state: dict = {}
deletepara_state: dict = {}

GROUP_SEND_ID = -1002114430690

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

def _load_token_df() -> pd.DataFrame:
    if os.path.exists(PREMIUM_TOKEN_PATH):
        return pd.read_excel(PREMIUM_TOKEN_PATH)
    os.makedirs(os.path.dirname(PREMIUM_TOKEN_PATH), exist_ok=True)
    return pd.DataFrame(columns=[
        "userid", "username",
        "token_purchased", "amount_paid",
        "tokens_remaining", "last_updated"
    ])

def _get_user_tokens(user_id: int) -> int:
    """Returns current remaining tokens for user."""
    df   = _load_token_df()
    mask = df["userid"] == user_id
    return int(df[mask].iloc[0]["tokens_remaining"]) if mask.any() else 0


def _deduct_token(user_id: int):
    """Deduct 1 token when user submits a valid recording."""
    df   = _load_token_df()
    mask = df["userid"] == user_id
    if mask.any():
        current = int(df.loc[mask, "tokens_remaining"].values[0])
        if current > 0:
            df.loc[mask, "tokens_remaining"] = current - 1
            df.loc[mask, "last_updated"]     = datetime.now().strftime("%Y-%m-%d %H:%M")
            df.to_excel(PREMIUM_TOKEN_PATH, index=False)

 

def _add_tokens(user_id: int, username: str,
                tokens: int, amount: str):
    """
    Call this manually or from an /addtokens admin command
    when user sends payment screenshot.
    """
    df   = _load_token_df()
    mask = df["userid"] == user_id
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")

    if mask.any():
        # user already exists → add on top
        old_purchased  = int(df.loc[mask, "token_purchased"].values[0])
        old_remaining  = int(df.loc[mask, "tokens_remaining"].values[0])

        df.loc[mask, "token_purchased"]  = old_purchased + tokens
        df.loc[mask, "tokens_remaining"] = old_remaining + tokens
        df.loc[mask, "amount_paid"]      = (
            str(df.loc[mask, "amount_paid"].values[0]) + f" + {amount}"
        )
        df.loc[mask, "last_updated"]     = now
        df.loc[mask, "username"]         = username
    else:
        new_row = {
            "userid"          : user_id,
            "username"        : username,
            "token_purchased" : tokens,
            "amount_paid"     : amount,
            "tokens_remaining": tokens,
            "last_updated"    : now,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_excel(PREMIUM_TOKEN_PATH, index=False)

async def add_tokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /addtokens <userid> <tokens> <amount>
    Example: /addtokens 123456789 50 ₹10
    Only works in GROUP_SEND_ID (admin group)
    """
    try:
        chat_id = update.effective_chat.id
        if chat_id != GROUP_SEND_ID:
            await update.message.reply_text("❌ Not allowed here.")
            return

        args = context.args
        if not args or len(args) < 3:
            await update.message.reply_text(
                "❌ Usage: /addtokens <userid> <tokens> <amount>\n"
                "Example: /addtokens 123456789 50 ₹10"
            )
            return

        user_id  = int(args[0])
        tokens   = int(args[1])
        amount_raw   = args[2]
        amount     = f"₹{amount_raw}"              

        # try to get username from telegram
        try:
            chat_member = await context.bot.get_chat(user_id)
            username    = chat_member.username or chat_member.first_name or str(user_id)
        except Exception:
            username = str(user_id)

        _add_tokens(user_id, username, tokens, amount)

        # notify admin
        await update.message.reply_text(
            f"✅ <b>Tokens Added!</b>\n\n"
            f"👤 User     : <b>{username}</b> ({user_id})\n"
            f"🎟️ Tokens   : <b>+{tokens}</b>\n"
            f"💰 Amount   : <b>{amount}</b>\n"
            f"🔄 Remaining: <b>{_get_user_tokens(user_id)}</b>",
            parse_mode="HTML"
        )

      
    except ValueError:
        await update.message.reply_text("❌ Invalid format. userid and tokens must be numbers.")
    except Exception as e:
        print(f"[add_tokens_command] {e}")
        await update.message.reply_text("❌ Something went wrong.")

# ─── Premium DM handler — called when user clicks "Buy Premium" button ────────
async def premium_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered when user taps the Buy Premium button.
    Only works in private/DM chat.
    Sends QR code + payment instructions.
    """
    try:
        user     = update.effective_user
        chat_id  = update.effective_chat.id
        username = user.username or user.first_name or str(user.id)

        # only handle in private chat
        if update.effective_chat.type != "private":
            return

        # check if this is a /start premium deep link
        args = context.args
        if not args or args[0] != "premium":
            return

        caption = (
            f"💎 <b>Spoken Helper Premium</b>\n"
            f"{'━' * 20}\n\n"
            f"👤 <b>{username}</b>\n\n"
            f"📦 <b>Plan Details</b>\n"
            f"├ 💰 Price    →  <b>{PREMIUM_PRICE}</b>\n"
            f"├ 🎟️ Tokens   →  <b>{PREMIUM_TOKENS} Recording Tokens</b>\n"
            f"└ ✅ Valid    →  Until tokens are used\n\n"
            f"{'━' * 20}\n"
            f"📲 <b>How to Pay:</b>\n\n"
            f"1️⃣ Scan the QR code above\n"
            f"2️⃣ Pay <b>{PREMIUM_PRICE}</b> via UPI\n"
            f"3️⃣ Take a screenshot of payment\n"
            f'4️⃣ Send screenshot to <a href="{PREMIUM_CONTACT}">@spoken_helper</a>\n'
            f"5️⃣ Tokens will be added within <b>1 hour</b> ✅\n\n"
            f"{'━' * 20}\n"
            f"<i>For support contact: "
            f'<a href="{PREMIUM_CONTACT}">@spoken_helper</a></i>'
        )

        try:
            with open(QR_CODE_PATH, "rb") as qr:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=qr,
                    caption=caption,
                    parse_mode="HTML"
                )
        except FileNotFoundError:
            # QR image nahi mili to sirf text bhejo
            print(f"[premium_start_handler] QR not found at {QR_CODE_PATH}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode="HTML"
            )

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[premium_start_handler] {e}")
    except Exception as e:
        print(f"[premium_start_handler] Unexpected: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    chat = update.effective_chat
    user_id = update.effective_user.id
    args = context.args
    print("helllo")
    print(f"[start_command] args={args}, chat_type={chat.type}") 
    # premium deep link
    if args and args[0] == "premium":
        await premium_start_handler(update, context)
        return
    if chat.type not in ["group", "supergroup"]:
        try:
            member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
            if member.status in ["member", "administrator", "creator"]:
                await context.bot.send_message(chat_id, text="✅ Welcome back! Use /startTranslation to start the Translation.")
            else:
                await context.bot.send_message(chat_id, text="Please Join this Channel To Support Us: @currentaffairs_04")
                await context.bot.send_message(chat_id, text="Then use /startTranslation Command To start the Translation")
        except Exception as e:
            print(f"Error checking membership: {e}")
            await context.bot.send_message(chat_id, text="Please Join this Channel To Support Us: @currentaffairs_04")
            await context.bot.send_message(chat_id, text="Then use /startTranslation Command To start the Translation")
    else:
        # In group chats
        await context.bot.send_message(chat_id, text="use /startTranslation Command To start the Translation")


async def addpara_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if chat_id != BOT_MANAGEMENT_GROUP_ID:
            await _safe_reply(update, context, "❌ Not allowed here.")
            return

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🟢 Easy",     callback_data=f"addpara_level_easy_{user_id}"),
            InlineKeyboardButton("🟡 Medium",   callback_data=f"addpara_level_medium_{user_id}"),
        ], [
            InlineKeyboardButton("🔴 Hard",     callback_data=f"addpara_level_hard_{user_id}"),
            InlineKeyboardButton("🟣 Advanced", callback_data=f"addpara_level_advanced_{user_id}"),
        ]])

        await _safe_reply(update, context,
            "📚 <b>Add New Paragraph</b>\n\n"
            "Select the difficulty level:",
            reply_markup=keyboard
        )

    except Exception as e:
        print(f"[addpara_command] {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Callback: level selected for addpara
# ══════════════════════════════════════════════════════════════════════════════
async def addpara_level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        await query.answer()
    except Exception:
        pass

    # only the person who ran /addpara can select
    parts    = query.data.split("_")   # addpara_level_easy_12345
    owner_id = int(parts[-1])
    if user_id != owner_id:
        try:
            await query.answer("❌ Not your command!", show_alert=True)
        except Exception:
            pass
        return

    level = parts[2]
    if level not in PARA_MIN_WORDS:
        return

    min_words   = PARA_MIN_WORDS[level]
    level_label = LEVEL_LABELS.get(level, level.capitalize())

    addpara_state[user_id] = {
        "level": level,
        "step" : "awaiting_paragraph",
    }

    try:
        await query.edit_message_text(
            f"📚 <b>Add Paragraph — {level_label}</b>\n\n"
            f"📝 Now send the paragraph text.\n\n"
            f"⚠️ <b>Minimum words required: {min_words}</b>\n\n"
            f"<i>Just type or paste the paragraph and send it as a message.</i>",
            parse_mode="HTML"
        )
    except Exception:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"📚 <b>Add Paragraph — {level_label}</b>\n\n"
                    f"📝 Now send the paragraph text.\n\n"
                    f"⚠️ <b>Minimum words required: {min_words}</b>\n\n"
                    f"<i>Just type or paste the paragraph and send it as a message.</i>"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[addpara_level_callback] {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Message handler: receives the paragraph text
# ══════════════════════════════════════════════════════════════════════════════
async def addpara_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Call this from your main message handler when chat_id == BOT_MANAGEMENT_GROUP_ID.
    Returns True if handled, False otherwise.
    """
    try:
        if not update.message or not update.message.text:
            return False

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        text    = update.message.text.strip()

        # ignore commands
        if text.startswith("/"):
            return False

        # check if user has active addpara session
        session = addpara_state.get(user_id)
        if not session or session.get("step") != "awaiting_paragraph":
            return False

        level     = session["level"]
        min_words = PARA_MIN_WORDS[level]
        word_count = len(text.split())

        # ── word count check ──────────────────────────────────────────────
        if word_count < min_words:
            try:
                await update.message.reply_text(
                    f"❌ <b>Too short!</b>\n\n"
                    f"Your paragraph has <b>{word_count} words</b>.\n"
                    f"Minimum required for <b>{LEVEL_LABELS[level]}</b>: <b>{min_words} words</b>\n\n"
                    f"Please send a longer paragraph.",
                    parse_mode="HTML"
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"❌ <b>Too short!</b>\n\n"
                        f"Your paragraph has <b>{word_count} words</b>.\n"
                        f"Minimum required for <b>{LEVEL_LABELS[level]}</b>: <b>{min_words} words</b>\n\n"
                        f"Please send a longer paragraph."
                    ),
                    parse_mode="HTML"
                )
            return True   # handled but not saved — keep session alive

        # ── load excel and get next srno ──────────────────────────────────
        if os.path.exists(READING_FILEPATH):
            df = pd.read_excel(READING_FILEPATH)
            df.columns = [c.strip().lower().replace(" ", "") for c in df.columns]
        else:
            os.makedirs(os.path.dirname(READING_FILEPATH), exist_ok=True)
            df = pd.DataFrame(columns=["srno", "paragraph", "level"])

        # get next srno — continue from max existing
        next_srno = int(df["srno"].max()) + 1 if not df.empty else 1

        new_row = {
            "srno"     : next_srno,
            "paragraph": text,
            "level"    : level.capitalize(),
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df = df.sort_values("srno").reset_index(drop=True)
        df.to_excel(READING_FILEPATH, index=False)

        # ── clear session ─────────────────────────────────────────────────
        addpara_state.pop(user_id, None)

        level_label = LEVEL_LABELS.get(level, level.capitalize())
        short_para  = text[:200] + ("..." if len(text) > 200 else "")

        success_msg = (
            f"✅ <b>Paragraph Added Successfully!</b>\n\n"
            f"├ Sr No   →  <b>{next_srno}</b>\n"
            f"├ Level   →  <b>{level_label}</b>\n"
            f"├ Words   →  <b>{word_count}</b>\n\n"
            f"📝 <b>Preview:</b>\n"
            f"<blockquote>{short_para}</blockquote>"
        )

        try:
            await update.message.reply_text(success_msg, parse_mode="HTML")
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id, text=success_msg, parse_mode="HTML"
            )

        # ── notify premium contact ────────────────────────────────────────
        try:
            notify_msg = (
                f"📚 <b>New Paragraph Added!</b>\n\n"
                f"├ Sr No   →  <b>{next_srno}</b>\n"
                f"├ Level   →  <b>{level_label}</b>\n"
                f"├ Words   →  <b>{word_count}</b>\n\n"
                f"📝 <b>Full Paragraph:</b>\n"
                f"<blockquote>{text}</blockquote>"
            )
            await context.bot.send_message(
                chat_id=NIMISH_CHAT_ID,
                text=notify_msg,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[addpara_message_handler] Could not notify premium contact: {e}")

        return True

    except Exception as e:
        print(f"[addpara_message_handler] {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  /deletepara <srno>
# ══════════════════════════════════════════════════════════════════════════════
async def deletepara_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if chat_id != BOT_MANAGEMENT_GROUP_ID:
            await _safe_reply(update, context, "❌ Not allowed here.")
            return

        args = context.args
        if not args:
            await _safe_reply(update, context,
                "❌ Usage: /deletepara <srno>\nExample: /deletepara 42"
            )
            return

        try:
            srno = int(args[0])
        except ValueError:
            await _safe_reply(update, context, "❌ Sr No must be a number.")
            return

        # check if srno exists
        if not os.path.exists(READING_FILEPATH):
            await _safe_reply(update, context, "❌ No paragraphs file found.")
            return

        df = pd.read_excel(READING_FILEPATH)
        df.columns = [c.strip().lower().replace(" ", "") for c in df.columns]
        mask = df["srno"] == srno

        if not mask.any():
            await _safe_reply(update, context,
                f"❌ No paragraph found with Sr No <b>{srno}</b>.",
            )
            return

        row         = df[mask].iloc[0]
        para_text   = str(row["paragraph"]).strip()
        para_level  = str(row["level"]).strip()
        short_para  = para_text[:200] + ("..." if len(para_text) > 200 else "")

        # save in state for confirmation
        deletepara_state[user_id] = {"srno": srno}

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "✅ Yes, Delete",
                callback_data=f"deletepara_confirm_{srno}_{user_id}"
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data=f"deletepara_cancel_{user_id}"
            ),
        ]])

        await _safe_reply(update, context,
            f"🗑️ <b>Are you sure you want to delete this paragraph?</b>\n\n"
            f"├ Sr No  →  <b>{srno}</b>\n"
            f"├ Level  →  <b>{para_level}</b>\n\n"
            f"📝 <b>Preview:</b>\n"
            f"<blockquote>{short_para}</blockquote>",
            reply_markup=keyboard
        )

    except Exception as e:
        print(f"[deletepara_command] {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Callback: confirm / cancel delete
# ══════════════════════════════════════════════════════════════════════════════
async def deletepara_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        await query.answer()
    except Exception:
        pass

    parts    = query.data.split("_")
    owner_id = int(parts[-1])

    if user_id != owner_id:
        try:
            await query.answer("❌ Not your command!", show_alert=True)
        except Exception:
            pass
        return

    # ── cancel ────────────────────────────────────────────────────────────
    if "cancel" in query.data:
        deletepara_state.pop(user_id, None)
        try:
            await query.edit_message_text("❌ <b>Delete cancelled.</b>", parse_mode="HTML")
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id, text="❌ <b>Delete cancelled.</b>", parse_mode="HTML"
            )
        return

    # ── confirm ───────────────────────────────────────────────────────────
    # callback_data = "deletepara_confirm_42_12345"
    srno = int(parts[2])

    if not os.path.exists(READING_FILEPATH):
        try:
            await query.edit_message_text("❌ File not found.", parse_mode="HTML")
        except Exception:
            pass
        return

    df   = pd.read_excel(READING_FILEPATH)
    df.columns = [c.strip().lower().replace(" ", "") for c in df.columns]
    mask = df["srno"] == srno

    if not mask.any():
        try:
            await query.edit_message_text(
                f"❌ Sr No <b>{srno}</b> not found.", parse_mode="HTML"
            )
        except Exception:
            pass
        return

    row        = df[mask].iloc[0]
    para_level = str(row["level"]).strip()

    # delete the row
    df = df[~mask].reset_index(drop=True)
    df.to_excel(READING_FILEPATH, index=False)

    deletepara_state.pop(user_id, None)

    success_msg = (
        f"✅ <b>Paragraph Deleted!</b>\n\n"
        f"├ Sr No  →  <b>{srno}</b>\n"
        f"└ Level  →  <b>{para_level}</b>\n\n"
        f"<i>Total paragraphs remaining: {len(df)}</i>"
    )

    try:
        await query.edit_message_text(success_msg, parse_mode="HTML")
    except Exception:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=success_msg, parse_mode="HTML"
            )
        except Exception as e:
            print(f"[deletepara_callback] {e}")