from Handlers.command import save_group_data,RegisteredGroupfile,RegisteredGroupfile ,groupsendid, save_groups, registered_groups, botManagementGroupId
from telegram import Update,InputFile
from telegram.ext import  ContextTypes
from datetime import date
from html import escape
import asyncio, json
import pandas as pd
import os, random
import zipfile
import io
from telegram.error import Forbidden, BadRequest
from Handlers.config import REPORT_FILES

ThoughtoftheDay_excel_PATH = "UserScore/thoughts.xlsx"

Thought_OF_THE_DAY_TEMPLATE = """
        📚 <b>Read Aloud</b> 📚

📝 <b>Thought:</b> <i>{thought}</i>

✍️ <b>By:</b> 
           <i>{writer}</i>

💬 Now Read above given thought !! 💡
"""

def get_next_unsent_word():
    df = pd.read_excel(ThoughtoftheDay_excel_PATH)
    next_row = df[df['issent'] != 1].head(1)

    if next_row.empty:
        return None, None  # No unsent word found

    row = next_row.iloc[0]
    word_data = {
        "srno": row['srno'],
        "thought": row['thought'],
        "writer": row['writer']
    }
    return word_data, df

def mark_word_as_sent(srno, df):
    df.loc[df['srno'] == srno, 'issent'] = 1
    df.loc[df['srno'] == srno, 'sentdate'] = str(date.today())  # ← add this
    df.to_excel(ThoughtoftheDay_excel_PATH, index=False)

async def scheduled_send_thought(app):
    class DummyMessage:
        async def reply_text(self, text, parse_mode=None):
            print("1")
    class DummyUpdate:
        effective_chat = type('obj', (), {'id': botManagementGroupId})()
        message = DummyMessage()
    class DummyContext:
        bot = app.bot
    
    await send_thought_of_the_day(DummyUpdate(), DummyContext())
    

async def send_thought_of_the_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registered_groups, botManagementGroupId
    
    chat_id = update.effective_chat.id
    if chat_id != botManagementGroupId:
        return
    word_data, df = get_next_unsent_word()
    if not word_data:
        await update.message.reply_text("✅ All words have already been sent.")
        
        return
    safe_data = {k: escape(str(v)) for k, v in word_data.items()}
    message = Thought_OF_THE_DAY_TEMPLATE.format(**safe_data)
   
    to_remove = set()
    for group_id in list(registered_groups):
        try:
            member = await context.bot.get_chat_member(chat_id=group_id, user_id=context.bot.id)
            if member.status in ['left', 'kicked']:
                to_remove.add(group_id)
        except (Forbidden, BadRequest):
            
            to_remove.add(group_id)
        except Exception as e:
            print(f"Error checking group {group_id}: {e}")

    for group_id in to_remove:
        registered_groups.discard(group_id)

    count = 0
    async def send_to_group(gid):
        try:
            await context.bot.send_message(
    chat_id=gid,
    text=message,
    parse_mode="HTML",
    disable_web_page_preview=True
)
            return True, gid
        except Exception as e:
            if "bot was kicked" in str(e) or "chat not found" in str(e).lower():
                return False, gid
            return None, gid

    tasks = [asyncio.create_task(send_to_group(gid)) for gid in registered_groups]
    results = await asyncio.gather(*tasks)

    for success, gid in results:
        if success is True:
            count += 1
        elif success is False:
            to_remove.add(gid)

    registered_groups -= to_remove
    await save_groups()
    save_group_data()


    mark_word_as_sent(word_data['srno'], df)
  
    await send_all_files_as_zip(context, chat_id=groupsendid, zip_name="daily_report.zip")

    await context.bot.send_message( chat_id=botManagementGroupId,
    text=
    f"✅ Thought of the Day sent to {count} groups: *{word_data['thought']}*",
    parse_mode="Markdown"
    )


async def send_all_files_as_zip(context, chat_id, zip_name="report.zip"):
    """Zip all report files and send as one document."""
    zip_buffer = io.BytesIO()
    added = []

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filepath in REPORT_FILES:
            if os.path.exists(filepath):
                zf.write(filepath, arcname=os.path.basename(filepath))
                added.append(os.path.basename(filepath))

    if not added:
        print("[ZIP] No files found to zip.")
        return

    zip_buffer.seek(0)
    try:
        await context.bot.send_document(
            chat_id=chat_id,
            document=InputFile(zip_buffer, filename=zip_name),
            caption=f"📦 <b>Daily Report</b>\n\n",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[ZIP] Failed to send zip: {e}")


async def update_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Reply to a .zip file with /updatereport
    → extracts all Excel files from zip
    → replaces matching files from REPORT_FILES list
    """
    chat_id = update.effective_chat.id

    # ── Only allowed in management group ──────────────────────────────────────
    if chat_id != groupsendid:
        await update.message.reply_text("❌ This command is not allowed here.")
        return

    # ── Must be a reply to a zip file ─────────────────────────────────────────
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Please reply to a <b>.zip</b> file with /updatereport",
            parse_mode="HTML"
        )
        return

    replied = update.message.reply_to_message
    if not replied.document:
        await update.message.reply_text("❌ Please reply to a <b>.zip</b> file.", parse_mode="HTML")
        return

    file_name = replied.document.file_name or ""
    if not file_name.lower().endswith(".zip"):
        await update.message.reply_text("❌ Only <b>.zip</b> files are supported.", parse_mode="HTML")
        return

    # ── Download zip ───────────────────────────────────────────────────────────
    try:
        file       = await context.bot.get_file(replied.document.file_id)
        file_bytes = await file.download_as_bytearray()
    except Exception as e:
        print(f"[updatereport] Download failed: {e}")
        await update.message.reply_text("❌ Could not download the zip file.")
        return

    # ── Build lookup: filename → full path  (from REPORT_FILES) ───────────────
    report_lookup = {os.path.basename(f): f for f in REPORT_FILES}

    updated  = []
    skipped  = []
    not_in_list = []

    # ── Extract and replace ────────────────────────────────────────────────────
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            for zip_entry in zf.namelist():
                base_name = os.path.basename(zip_entry)

                # Skip folders or non-excel files
                if not base_name or not base_name.endswith(".xlsx"):
                    continue

                if base_name in report_lookup:
                    target_path = report_lookup[base_name]

                    # Ensure directory exists
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)

                    # Replace file
                    with zf.open(zip_entry) as src, open(target_path, 'wb') as dst:
                        dst.write(src.read())

                    updated.append(base_name)
                else:
                    not_in_list.append(base_name)

    except zipfile.BadZipFile:
        await update.message.reply_text("❌ Invalid or corrupted zip file.")
        return
    except Exception as e:
        print(f"[updatereport] Extraction failed: {e}")
        await update.message.reply_text("❌ Something went wrong while extracting.")
        return

    # ── Reply with result ──────────────────────────────────────────────────────
    if not updated:
        await update.message.reply_text(
            "⚠️ No matching files found in zip.\n\n"
            "Make sure filenames match exactly with the report list.",
            parse_mode="HTML"
        )
        return

    updated_text  = "\n".join(f"  ✅ {f}" for f in updated)
    ignored_text  = "\n".join(f"  ⚠️ {f}" for f in not_in_list) if not_in_list else "  None"

    await update.message.reply_text(
        f"📦 <b>Report Update Complete!</b>\n\n"
        f"<b>Updated ({len(updated)}):</b>\n{updated_text}\n\n"
        f"<b>Not in list ({len(not_in_list)}):</b>\n{ignored_text}",
        parse_mode="HTML"
    )