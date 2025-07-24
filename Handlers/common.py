from Handlers.command import save_group_data,GROUPS_FILE , save_groups, group_data, registered_groups, botManagementGroupId
from telegram import Update,InputFile
from telegram.ext import  ContextTypes
from Handlers.config import ALLOWED_FILES
import asyncio, json
import pandas as pd
import os, random
from telegram.error import Forbidden, BadRequest

WordoftheDay_excel_PATH = "UserScore/wordoftheday.xlsx"

WORD_OF_THE_DAY_TEMPLATE = """
📚 *Word of the Day* 📚
       
📝 Word: {word}

📖 *Meaning*: _{meaning}_

🔁 *Synonyms*: _{synonyms}_

🚫 *Antonyms*: _{antonym}_

✍️ *Example*:
_{example}_

💬 Now Create 2 Sentence on this Word!!💡
"""
def shuffle_excel_rows_inplace(input_file: str):
    strategies = ["reverse", "reverse of 10 and 10", "random shuffle"]
    try:
        df = pd.read_excel(input_file)
        chosen_strategy = random.choice(strategies)
        print(f"🔀 {input_file} — Strategy: {chosen_strategy}")

        if chosen_strategy == "reverse":
            shuffled_df = df[::-1].reset_index(drop=True)

        elif chosen_strategy == "reverse of 10 and 10":
            chunks = [df[i:i+10][::-1] for i in range(0, len(df), 10)]
            shuffled_df = pd.concat(chunks, ignore_index=True)

        elif chosen_strategy == "random shuffle":
            shuffled_df = df.sample(frac=1).reset_index(drop=True)

        shuffled_df.to_excel(input_file, index=False)
        print(f"✅ Overwritten: {input_file}\n")

    except Exception as e:
        print(f"❌ Error in {input_file}: {e}")

def shuffle_all_files_inplace():
    for filename in ALLOWED_FILES:
        input_path = os.path.join("Data", f"{filename}.xlsx")
        shuffle_excel_rows_inplace(input_path)


def get_next_unsent_word():
    df = pd.read_excel(WordoftheDay_excel_PATH)
    next_row = df[df['issent'] != 1].head(1)

    if next_row.empty:
        return None, None  # No unsent word found

    row = next_row.iloc[0]
    word_data = {
        "srno": row['srno'],
        "word": row['word'],
        "meaning": row['meaning'],
        "synonyms": row['synonyms'],
        "antonym": row['antonyms'],
        "example": row['example'],
    }
    return word_data, df

def mark_word_as_sent(srno, df):
    df.loc[df['srno'] == srno, 'issent'] = 1
    df.to_excel(WordoftheDay_excel_PATH, index=False)

async def scheduled_send_word(app):
    class DummyMessage:
        async def reply_text(self, text, parse_mode=None):
            print(text)
    class DummyUpdate:
        effective_chat = type('obj', (), {'id': botManagementGroupId})()
        message = DummyMessage()

    class DummyContext:
        bot = app.bot
    
    await send_word_of_the_day(DummyUpdate(), DummyContext())
    await shuffle_command(DummyUpdate(), DummyContext())
    

async def shuffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    shuffle_all_files_inplace()
    
    await context.bot.send_message( chat_id=botManagementGroupId,
    text=
    f"✅ file shuffle successfully*",
    parse_mode="Markdown"
    )

async def send_word_of_the_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registered_groups, botManagementGroupId
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "r") as f:
            registered_groups = set(json.load(f))
    else:
        registered_groups = set()

    chat_id = update.effective_chat.id
    if chat_id != botManagementGroupId:
        return

    word_data, df = get_next_unsent_word()
    if not word_data:
        await update.message.reply_text("✅ All words have already been sent.")
        return

    message = WORD_OF_THE_DAY_TEMPLATE.format(**word_data)

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
            await context.bot.send_message(chat_id=gid, text=message, parse_mode="Markdown")
            return True, gid
        except Exception as e:
            print(f"Error sending to {gid}: {e}")
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
    save_groups()
    save_group_data()

    # ✅ Mark word as sent
    mark_word_as_sent(word_data['srno'], df)
    try:
        with open(WordoftheDay_excel_PATH, 'rb') as f:
            await context.bot.send_document(
            chat_id='@mygroup_0404',  # Your public group username
            document=InputFile(f, filename=WordoftheDay_excel_PATH)
        )
    except Exception as e:
        print(f"❌ Failed to send Excel file to @mugroup_0404: {e}")

# ✅ Final confirmation message to admin
    await context.bot.send_message( chat_id=botManagementGroupId,
    text=
    f"✅ Word of the Day sent to {count} groups: *{word_data['word']}*",
    parse_mode="Markdown"
    )