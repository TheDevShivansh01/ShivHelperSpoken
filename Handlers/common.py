from Handlers.command import save_group_data,Promotion,RegisteredGroupfile,RegisteredGroupfile ,groupsendid, save_groups, group_data, registered_groups, botManagementGroupId
from telegram import Update,InputFile
from telegram.ext import  ContextTypes
from Handlers.config import ALLOWED_FILES
import asyncio, json
import pandas as pd
import os, random
from telegram.error import Forbidden, BadRequest

WordoftheDay_excel_PATH = "UserScore/wordoftheday.xlsx"
Topic_EXCEL_PATH = "UserScore/gs1.xlsx"

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
        

        if chosen_strategy == "reverse":
            shuffled_df = df[::-1].reset_index(drop=True)

        elif chosen_strategy == "reverse of 10 and 10":
            chunks = [df[i:i+10][::-1] for i in range(0, len(df), 10)]
            shuffled_df = pd.concat(chunks, ignore_index=True)

        elif chosen_strategy == "random shuffle":
            shuffled_df = df.sample(frac=1).reset_index(drop=True)

        shuffled_df.to_excel(input_file, index=False)
        

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
            print("1")
    class DummyUpdate:
        effective_chat = type('obj', (), {'id': botManagementGroupId})()
        message = DummyMessage()
    class DummyUpdate2:
        effective_chat = type('obj', (), {'id': botManagementGroupId})()
        message = DummyMessage()


    class DummyContext:
        bot = app.bot
    
    await send_word_of_the_day(DummyUpdate(), DummyContext())
    await shuffle_command(DummyUpdate2(), DummyContext())
    

async def schedule_send_UpscTopic(app):
    
    class DummyMessage:
        async def reply_text(self, text, parse_mode=None):
            print("hi")
    class DummyUpdate:
        effective_chat = type('obj', (), {'id': botManagementGroupId})()
        message = DummyMessage()
    class DummyUpdate2:
        effective_chat = type('obj', (), {'id': botManagementGroupId})()
        message = DummyMessage()

    class DummyContext:
        bot = app.bot

    await schedule_send_Topic_of_the_day(DummyUpdate(), DummyContext())



async def schedule_send_Topic_of_the_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topicregistered_groups = set()
    global registered_groups, botManagementGroupId
    if os.path.exists(RegisteredGroupfile):
        df = pd.read_excel(RegisteredGroupfile)
        df_filtered = df[df["isupscmainstopicallowed"] == 1]
        topicregistered_groups = set(df_filtered["groupid"].dropna().astype(str).tolist())
    else:
        topicregistered_groups = set()

    chat_id = update.effective_chat.id
    if chat_id != botManagementGroupId:
        return  

    

    message = create_daily_template()
   

    count = 0
    async def send_to_group(gid):
        try:
            await context.bot.send_message(chat_id=gid, text=message, parse_mode="Markdown")
            return True, gid
        except Exception as e:
            if "bot was kicked" in str(e) or "chat not found" in str(e).lower():
                return False, gid
            return None, gid     

    tasks = [asyncio.create_task(send_to_group(gid)) for gid in topicregistered_groups]
    results = await asyncio.gather(*tasks)

    for success, gid in results:
        if success is True:
            count += 1
    try:
        with open(Topic_EXCEL_PATH, 'rb') as f:
            await context.bot.send_document(
            chat_id='@mygroup_0404',  
            document=InputFile(f, filename=Topic_EXCEL_PATH)
        )
    except Exception as e:
        print(f"❌ Failed to send Excel file to @mugroup_0404: {e}")

    await context.bot.send_message( chat_id=botManagementGroupId,
    text=
    f"✅ UPSC Topic Sent to {count} groups",
    parse_mode="Markdown"
    )

def create_daily_template():
    df = pd.read_excel(Topic_EXCEL_PATH)

    unsent_df = df[df["issend"] != 1]

    if unsent_df.shape[0] < 2:
        return "✅ All questions have been sent!"

    sent_count = df[df["issend"] == 1].shape[0]
    day_num = sent_count // 2 + 1

    available_gs = unsent_df["gs"].unique().tolist()
    if len(available_gs) < 2:
        return "⚠️ Not enough unique GS papers left."
    chosen_gs = random.sample(available_gs, 2)

    selected_rows = []
    for gs in chosen_gs:
        rows = unsent_df[unsent_df["gs"] == gs]
        if not rows.empty:
            selected_rows.append(rows.sample(1).iloc[0])

    for row in selected_rows:
        df.loc[df["srno"] == row["srno"], "issend"] = 1
    df.to_excel(Topic_EXCEL_PATH, index=False)

    gs_emojis = {1: "🎨", 2: "🌍", 3: "📊", 4: "⚖️"}

    template = f"📘 *Day {day_num} | UPSC MAINS Preparation*\n"
    template += "━━━━━━━━━━━━━━━━━━━━━━━\n"

    for i, row in enumerate(selected_rows, 1):
        emoji = gs_emojis.get(row["gs"], "📖")
        if(i==1):
            mark = 15
        else:
            mark = 10
        template += (
            f"\n*Topic {i}:* {row['topic']}\n"
            f"📅 *Year:* {row['year']}\n"
            f"{emoji} *GS Paper:* {row['gs']}\n\n"
            f"❓ *Question:* _{row['question']}_\n"
            "━━━━━━━━━━\n"
        )

    template += "💡 *Tip:* Try writing answers within 150–200 words. \n\n command to stop this topic /stoptopic \n command to allow this topic /allowtopic \n"
    return template

async def shuffle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    shuffle_all_files_inplace()
    
    await context.bot.send_message( chat_id=groupsendid,
    text=
    f"✅ file shuffle successfully*"
    )

async def send_word_of_the_day(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global registered_groups, botManagementGroupId
    print("send word of the dat")
    if os.path.exists(RegisteredGroupfile):
                with open(RegisteredGroupfile, 'rb') as file:
                    print("file send")
                    await context.bot.send_document(chat_id=groupsendid, document=file)


    chat_id = update.effective_chat.id
    if chat_id != botManagementGroupId:
        print("chat id error")
        return

    word_data, df = get_next_unsent_word()
    if not word_data:
        await update.message.reply_text("✅ All words have already been sent.")
        print("this run")
        return

    message = WORD_OF_THE_DAY_TEMPLATE.format(**word_data)

    to_remove = set()
    for group_id in list(registered_groups):
        try:
            print(group_id)
            member = await context.bot.get_chat_member(chat_id=group_id, user_id=context.bot.id)
            if member.status in ['left', 'kicked']:
                to_remove.add(group_id)
        except (Forbidden, BadRequest):
            print("hello badrequest")
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
    await save_groups()
    save_group_data()


    mark_word_as_sent(word_data['srno'], df)
    try:
        with open(WordoftheDay_excel_PATH, 'rb') as f:
            await context.bot.send_document(
            chat_id='@mygroup_0404',  # Your public group username
            document=InputFile(f, filename=WordoftheDay_excel_PATH)
        )
    except Exception as e:
        print(f"❌ Failed to send Excel file to @mugroup_0404: {e}")


    await context.bot.send_message( chat_id=botManagementGroupId,
    text=
    f"✅ Word of the Day sent to {count} groups: *{word_data['word']}*",
    parse_mode="Markdown"
    )
async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is admin/creator in the group."""
    chat = update.effective_chat
    user = update.effective_user

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ["administrator", "creator"]
    except BadRequest:
        return False
    
async def allowupsctopicCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # Only allow in groups
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command can only be used in groups.")
        return
    if not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only group admins can allow UPSC topics.")
        return
    chat_id = str(chat.id)

    if os.path.exists(RegisteredGroupfile):
        df = pd.read_excel(RegisteredGroupfile)

        # Ensure groupid is compared as string
        df["groupid"] = df["groupid"].astype(str)

        if chat_id in df["groupid"].values:
            df.loc[df["groupid"] == chat_id, "isupscmainstopicallowed"] = 1
            df.to_excel(RegisteredGroupfile, index=False)
            await update.message.reply_text("✅ UPSC Mains topic allowed for this group.")
        else:
            # Add new entry if not present
            new_row = {
                "srno": len(df) + 1,
                "groupid": chat_id,
                "last_message_id": None,
                "isupscmainstopicallowed": 1
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_excel(RegisteredGroupfile, index=False)
            await update.message.reply_text("✅ Group registered and UPSC Mains topic allowed.")
    else:
        # Create new file if it doesn't exist
        df = pd.DataFrame([{
            "srno": 1,
            "groupid": chat_id,
            "last_message_id": None,
            "isupscmainstopicallowed": 1
        }])
        df.to_excel(RegisteredGroupfile, index=False)
        await update.message.reply_text("✅ New file created and UPSC Mains topic allowed for this group.")

async def stopupsctopicCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # Only allow in groups
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command can only be used in groups.")
        return
    if not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only group admins can Stop UPSC topics.")
        return
    chat_id = str(chat.id)

    if os.path.exists(RegisteredGroupfile):
        df = pd.read_excel(RegisteredGroupfile)

        # Ensure groupid is string
        df["groupid"] = df["groupid"].astype(str)

        if chat_id in df["groupid"].values:
            # Set column to NULL (NaN in pandas)
            df.loc[df["groupid"] == chat_id, "isupscmainstopicallowed"] = pd.NA
            df.to_excel(RegisteredGroupfile, index=False)
            await update.message.reply_text("⛔ UPSC Mains topic stopped for this group.")
        else:
            await update.message.reply_text("❌ This group is not registered.")
    else:
        await update.message.reply_text("❌ Complain about this to bot owner")
