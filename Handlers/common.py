from Handlers.command import save_group_data,RegisteredGroupfile,RegisteredGroupfile ,groupsendid, save_groups, registered_groups, botManagementGroupId
from telegram import Update,InputFile
from telegram.ext import  ContextTypes
from datetime import date
from html import escape
import asyncio, json
import pandas as pd
import os, random
from telegram.error import Forbidden, BadRequest

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
    
    if os.path.exists(RegisteredGroupfile):
                with open(RegisteredGroupfile, 'rb') as file:
                    await context.bot.send_document(chat_id=groupsendid, document=file)


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
    try:
        with open(ThoughtoftheDay_excel_PATH, 'rb') as f:
            await context.bot.send_document(
            chat_id='@mygroup_0404',  # Your public group username
            document=InputFile(f, filename=ThoughtoftheDay_excel_PATH)
        )
    except Exception as e:
        print(f"❌ Failed to send Excel file to @mygroup_0404: {e}")


    await context.bot.send_message( chat_id=botManagementGroupId,
    text=
    f"✅ Thought of the Day sent to {count} groups: *{word_data['thought']}*",
    parse_mode="Markdown"
    )
