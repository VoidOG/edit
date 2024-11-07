from telegram import Update, InputMediaPhoto, InputMediaDocument
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from telegram.error import TelegramError
from telegram.constants import ParseMode
from pymongo import MongoClient
import re

ASK_EDIT_TYPE, ASK_MESSAGE_LINK, EDIT_MESSAGE = range(3)

client = MongoClient("mongodb+srv://Cenzo:Cenzo123@cenzo.azbk1.mongodb.net/")
db = client["telegram_bot"]
sudo_users_collection = db["sudo_users"]

OWNER_ID =6663845789

async def is_sudo_user(user_id: int) -> bool:
    return sudo_users_collection.find_one({"user_id": user_id}) is not None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id != OWNER_ID and not await is_sudo_user(user_id):
        await update.message.reply_text("You don't have permission to use this bot.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Do you want to:\n"
        "1. Edit Text\n"
        "2. Replace Media/File\n\n"
        "Send '1' for Text or '2' for Media/File."
    )
    return ASK_EDIT_TYPE

async def sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Only the bot owner can grant sudo access.")
        return

    if context.args:
        try:
            user_id = int(context.args[0])
            if sudo_users_collection.find_one({"user_id": user_id}):
                await update.message.reply_text("User already has sudo access.")
            else:
                sudo_users_collection.insert_one({"user_id": user_id})
                await update.message.reply_text(f"Sudo access granted to user {user_id}.")
        except ValueError:
            await update.message.reply_text("Invalid user ID format.")
    else:
        await update.message.reply_text("Usage: /sudo <user_id>")

async def rmsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Only the bot owner can revoke sudo access.")
        return

    if context.args:
        try:
            user_id = int(context.args[0])
            result = sudo_users_collection.delete_one({"user_id": user_id})
            if result.deleted_count > 0:
                await update.message.reply_text(f"Sudo access revoked for user {user_id}.")
            else:
                await update.message.reply_text("User does not have sudo access.")
        except ValueError:
            await update.message.reply_text("Invalid user ID format.")
    else:
        await update.message.reply_text("Usage: /rmsudo <user_id>")

async def ask_message_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == '1':
        context.user_data['edit_type'] = 'text'
    elif choice == '2':
        context.user_data['edit_type'] = 'media'
    else:
        await update.message.reply_text("Invalid choice. Please send '1' for Text or '2' for Media/File.")
        return ASK_EDIT_TYPE

    await update.message.reply_text("Please provide the message link of the group chat to edit:")
    return ASK_MESSAGE_LINK

def parse_message_link(link: str):
    # Check for public link format
    public_match = re.match(r"https://t\.me/([\w\d_]+)/(\d+)", link)
    if public_match:
        chat_id = f"@{public_match.group(1)}"
        message_id = int(public_match.group(2))
        return chat_id, message_id

    # Check for private link format
    private_match = re.match(r"https://t\.me/c/(-?\d+)/(\d+)", link)
    if private_match:
        chat_id = int(private_match.group(1))
        message_id = int(private_match.group(2))
        return chat_id, message_id

    return None, None

async def edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_link = update.message.text
    chat_id, message_id = parse_message_link(message_link)

    if not chat_id or not message_id:
        await update.message.reply_text("Invalid message link. Please provide a valid public or private link.")
        return ASK_MESSAGE_LINK

    context.user_data['chat_id'] = chat_id
    context.user_data['message_id'] = message_id

    edit_type = context.user_data.get('edit_type')
    if edit_type == 'text':
        await update.message.reply_text("Send the new text to update the message.")
    elif edit_type == 'media':
        await update.message.reply_text("Send the new media/file to update the message.")

    return EDIT_MESSAGE

async def apply_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = context.user_data.get('chat_id')
    message_id = context.user_data.get('message_id')
    edit_type = context.user_data.get('edit_type')

    try:
        if edit_type == 'text':
            new_text = update.message.text
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text, parse_mode=ParseMode.HTML)
            await update.message.reply_text("Message text updated successfully!")
        elif edit_type == 'media':
            if update.message.photo:
                media = InputMediaPhoto(update.message.photo[-1].file_id)
            elif update.message.document:
                media = InputMediaDocument(update.message.document.file_id)
            else:
                await update.message.reply_text("Please send a valid media/file to replace.")
                return EDIT_MESSAGE

            await context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media)
            await update.message.reply_text("Message media/file updated successfully!")

        return ConversationHandler.END
    except TelegramError as e:
        await update.message.reply_text(f"Error: {e}")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Edit operation cancelled.")
    return ConversationHandler.END

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import re

# Your existing imports and MongoDB setup here

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Only the owner and sudo users can use this command
    if user_id != OWNER_ID and not await is_sudo_user(user_id):
        await update.message.reply_text("You don't have permission to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /send <message> <group_username/chat_id/group_link>")
        return

    # Extract the message and target group information
    message_text = " ".join(context.args[:-1])
    group_identifier = context.args[-1]

    # Process the group identifier
    chat_id = None

    # Check if it is a chat ID (numeric)
    if group_identifier.isdigit() or (group_identifier[1:].isdigit() and group_identifier.startswith('-')):
        chat_id = int(group_identifier)

    # Check if it is a public username (starts with '@')
    elif group_identifier.startswith('@'):
        chat_id = group_identifier

    # Check if it's a group link
    else:
        match = re.match(r"https://t\.me/([\w\d_]+)", group_identifier)
        if match:
            chat_id = f"@{match.group(1)}"

    if not chat_id:
        await update.message.reply_text("Invalid group identifier. Please provide a valid chat ID, username, or link.")
        return

    # Try sending the message
    try:
        await context.bot.send_message(chat_id=chat_id, text=message_text)
        await update.message.reply_text("Message sent successfully!")
    except TelegramError as e:
        await update.message.reply_text(f"Failed to send the message: {e}")


def main():
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_EDIT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_message_link)],
            ASK_MESSAGE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_message)],
            EDIT_MESSAGE: [MessageHandler((filters.TEXT | filters.PHOTO | filters.DOCUMENT) & ~filters.COMMAND, apply_edit)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Add sudo management handlers
    app.add_handler(CommandHandler("sudo", sudo))
    app.add_handler(CommandHandler("rmsudo", rmsudo))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("send", send_message))

    app.run_polling()

if __name__ == "__main__":
    main()
