import re
import random
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden, TimedOut

# ── Config ─────────────────────────────────────────────────────────────────────
CHANNEL_ID              = "-1002234035497"
DailyCurrentGroupAffairId = ""
BOT_MANAGEMENT_GROUP_ID = -1002359766306


# ══════════════════════════════════════════════════════════════════════════════
#  PARSER
# ══════════════════════════════════════════════════════════════════════════════

def _parse_mcqs(text: str) -> list:
    """
    Parses MCQ text into list of dicts:
    {
      question       : str  (english),
      hindi_question : str  (hindi, may be empty),
      options        : [str],
      correct_index  : int,
      explanation    : str
    }
    """
    results = []

    # split by numbered blocks like "1.\n"
    blocks = re.split(r'\n\s*\d+\.\s*\n', "\n" + text.strip())
    blocks = [b.strip() for b in blocks if b.strip()]

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]

        question       = ""
        hindi_question = ""
        options        = []
        answer_key     = ""
        explanation    = ""

        for line in lines:

            # ── Question lines ─────────────────────────────────────────────
            eq = re.match(
                r'^(English Question|Hindi Question)\s*:\s*(.+)',
                line, re.IGNORECASE
            )
            if eq:
                label  = eq.group(1).lower()
                q_text = eq.group(2).strip()
                if "english" in label:
                    question = q_text
                elif "hindi" in label:
                    hindi_question = q_text
                continue

            # ── Options  A) / A. ───────────────────────────────────────────
            opt = re.match(r'^[A-D][).]\s*(.+)', line)
            if opt:
                options.append(opt.group(1).strip())
                continue

            # ── Answer ─────────────────────────────────────────────────────
            ans = re.match(r'^Answer\s*:\s*([A-D])', line, re.IGNORECASE)
            if ans:
                answer_key = ans.group(1).upper()
                continue

            # ── Explanation ────────────────────────────────────────────────
            exp = re.match(r'^Explanation\s*:\s*(.+)', line, re.IGNORECASE)
            if exp:
                explanation = exp.group(1).strip()
                continue

        if not question or len(options) < 2:
            continue

        correct_index = ord(answer_key) - ord('A') if answer_key else 0
        if correct_index >= len(options):
            correct_index = 0

        results.append({
            "question"      : question,
            "hindi_question": hindi_question,
            "options"       : options,
            "correct_index" : correct_index,
            "explanation"   : explanation,
        })

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _build_poll_question(english_q: str, hindi_q: str) -> str:
    """
    English question first, Hindi on next line.
    If combined length > 300 chars (Telegram limit), use English only.
    """
    if hindi_q:
        combined = f"{english_q}\n{hindi_q}"
        if len(combined) <= 300:
            return combined
    # fallback — english only, capped at 300
    return english_q[:300]


def _shuffle_options(options: list, correct_index: int):
    """
    Shuffle options randomly.
    Returns (shuffled_options, new_correct_index).
    """
    indexed   = list(enumerate(options))
    random.shuffle(indexed)
    new_options       = [opt for _, opt in indexed]
    old_to_new        = {old: new for new, (old, _) in enumerate(indexed)}
    new_correct_index = old_to_new[correct_index]
    return new_options, new_correct_index


# ══════════════════════════════════════════════════════════════════════════════
#  /sendtoday  — reply to MCQ text to send as polls to channel
# ══════════════════════════════════════════════════════════════════════════════

async def sendtoday_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id

        # only management group
        if chat_id != BOT_MANAGEMENT_GROUP_ID:
            try:
                await update.message.reply_text("❌ Not allowed here.")
            except Exception:
                pass
            return

        # must be a reply
        if not update.message.reply_to_message:
            try:
                await update.message.reply_text(
                    "❌ Reply to the MCQ text message with /sendtoday"
                )
            except Exception:
                pass
            return

        replied_text = update.message.reply_to_message.text
        if not replied_text:
            try:
                await update.message.reply_text("❌ Replied message has no text.")
            except Exception:
                pass
            return

        # parse MCQs
        mcqs = _parse_mcqs(replied_text)

        if not mcqs:
            try:
                await update.message.reply_text(
                    "❌ Could not parse any MCQs.\n"
                    "Make sure format has:\n"
                    "English Question: ...\n"
                    "Hindi Question: ...\n"
                    "A) ... B) ... C) ... D) ...\n"
                    "Answer: X\n"
                    "Explanation: ..."
                )
            except Exception:
                pass
            return

        # sending status message
        try:
            status_msg = await update.message.reply_text(
                f"⏳ Sending <b>{len(mcqs)}</b> polls to channel...",
                parse_mode="HTML"
            )
        except Exception:
            status_msg = None

        sent   = 0
        failed = 0
        errors = []

        for i, mcq in enumerate(mcqs):
            english_q     = mcq["question"]
            hindi_q       = mcq["hindi_question"]
            options       = mcq["options"]
            correct_index = mcq["correct_index"]
            explanation   = mcq["explanation"]

            # build question: english + hindi on next line if fits
            question = _build_poll_question(english_q, hindi_q)

            # shuffle options
            shuffled_options, new_correct = _shuffle_options(options, correct_index)

            try:
                await context.bot.send_poll(
                    chat_id                 = CHANNEL_ID,
                    question                = question,
                    options                 = shuffled_options,
                    type                    = "quiz",
                    correct_option_id       = new_correct,
                    explanation             = explanation if explanation else None,
                    is_anonymous            = True,
                    allows_multiple_answers = False,
                )
                sent += 1

            except Exception as e:
                print(f"[sendtoday_command] Poll {i+1} failed: {e}")
                failed += 1
                errors.append(f"Q{i+1}: {str(e)[:60]}")

            await asyncio.sleep(0.6)   # avoid flood limit

        # result message
        result = (
            f"✅ <b>Done!</b>\n\n"
            f"├ Total Parsed  → <b>{len(mcqs)}</b>\n"
            f"├ Sent          → <b>{sent}</b>\n"
            f"└ Failed        → <b>{failed}</b>\n"
        )

        if errors:
            result += "\n<b>Errors:</b>\n" + "\n".join(f"• {e}" for e in errors[:5])

        try:
            if status_msg:
                await status_msg.edit_text(result, parse_mode="HTML")
            else:
                await update.message.reply_text(result, parse_mode="HTML")
        except Exception:
            try:
                await context.bot.send_message(
                    chat_id=chat_id, text=result, parse_mode="HTML"
                )
            except Exception as e:
                print(f"[sendtoday_command] Could not send result: {e}")

    except (BadRequest, Forbidden, TimedOut) as e:
        print(f"[sendtoday_command] {e}")
        try:
            await update.message.reply_text(f"❌ Telegram error: {e}")
        except Exception:
            pass
    except Exception as e:
        print(f"[sendtoday_command] Unexpected: {e}")
        try:
            await update.message.reply_text("❌ Something went wrong.")
        except Exception:
            pass