from telegram import Update, InputMediaPhoto, InputMediaDocument, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from telegram.error import TelegramError
from pymongo import MongoClient
import re

ASK_EDIT_TYPE, ASK_MESSAGE_LINK, EDIT_MESSAGE = range(3)

# MongoDB setup
client = MongoClient("mongodb+srv://Cenzo:Cenzo123@cenzo.azbk1.mongodb.net/")
db = client["telegram_bot"]
sudo_users_collection = db["sudo_users"]

OWNER_ID = 6663845789

def is_sudo_user(user_id: int) -> bool:
    return sudo_users_collection.find_one({"user_id": user_id}) is not None

def start(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    if user_id != OWNER_ID and not is_sudo_user(user_id):
        update.message.reply_text("You don't have permission to use this bot.")
        return ConversationHandler.END

    update.message.reply_text(
        "Do you want to:\n"
        "1. Edit Text\n"
        "2. Replace Media/File\n\n"
        "Send '1' for Text or '2' for Media/File."
    )
    return ASK_EDIT_TYPE

def sudo(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("Only the bot owner can grant sudo access.")
        return

    if context.args:
        try:
            user_id = int(context.args[0])
            if sudo_users_collection.find_one({"user_id": user_id}):
                update.message.reply_text("User already has sudo access.")
            else:
                sudo_users_collection.insert_one({"user_id": user_id})
                update.message.reply_text(f"Sudo access granted to user {user_id}.")
        except ValueError:
            update.message.reply_text("Invalid user ID format.")
    else:
        update.message.reply_text("Usage: /sudo <user_id>")

def rmsudo(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("Only the bot owner can revoke sudo access.")
        return

    if context.args:
        try:
            user_id = int(context.args[0])
            result = sudo_users_collection.delete_one({"user_id": user_id})
            if result.deleted_count > 0:
                update.message.reply_text(f"Sudo access revoked for user {user_id}.")
            else:
                update.message.reply_text("User does not have sudo access.")
        except ValueError:
            update.message.reply_text("Invalid user ID format.")
    else:
        update.message.reply_text("Usage: /rmsudo <user_id>")

def ask_message_link(update: Update, context: CallbackContext) -> int:
    choice = update.message.text
    if choice == '1':
        context.user_data['edit_type'] = 'text'
    elif choice == '2':
        context.user_data['edit_type'] = 'media'
    else:
        update.message.reply_text("Invalid choice. Please send '1' for Text or '2' for Media/File.")
        return ASK_EDIT_TYPE

    update.message.reply_text("Please provide the message link of the group chat to edit:")
    return ASK_MESSAGE_LINK

def parse_message_link(link: str):
    public_match = re.match(r"https://t\.me/([\w\d_]+)/(\d+)", link)
    if public_match:
        chat_id = f"@{public_match.group(1)}"
        message_id = int(public_match.group(2))
        return chat_id, message_id

    private_match = re.match(r"https://t\.me/c/(-?\d+)/(\d+)", link)
    if private_match:
        chat_id = int(private_match.group(1))
        message_id = int(private_match.group(2))
        return chat_id, message_id

    return None, None

def edit_message(update: Update, context: CallbackContext) -> int:
    message_link = update.message.text
    chat_id, message_id = parse_message_link(message_link)

    if not chat_id or not message_id:
        update.message.reply_text("Invalid message link. Please provide a valid public or private link.")
        return ASK_MESSAGE_LINK

    context.user_data['chat_id'] = chat_id
    context.user_data['message_id'] = message_id

    edit_type = context.user_data.get('edit_type')
    if edit_type == 'text':
        update.message.reply_text("Send the new text to update the message.")
    elif edit_type == 'media':
        update.message.reply_text("Send the new media/file to update the message.")

    return EDIT_MESSAGE

def apply_edit(update: Update, context: CallbackContext) -> int:
    chat_id = context.user_data.get('chat_id')
    message_id = context.user_data.get('message_id')
    edit_type = context.user_data.get('edit_type')

    try:
        if edit_type == 'text':
            new_text = update.message.text
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text, parse_mode=ParseMode.HTML)
            update.message.reply_text("Message text updated successfully!")
        elif edit_type == 'media':
            if update.message.photo:
                media = InputMediaPhoto(update.message.photo[-1].file_id)
            elif update.message.document:
                media = InputMediaDocument(update.message.document.file_id)
            else:
                update.message.reply_text("Please send a valid media/file to replace.")
                return EDIT_MESSAGE

            context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media)
            update.message.reply_text("Message media/file updated successfully!")

        return ConversationHandler.END
    except TelegramError as e:
        update.message.reply_text(f"Error: {e}")
        return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Edit operation cancelled.")
    return ConversationHandler.END
    
def sudolist(update: Update, context: CallbackContext):
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("You don't have permission to view the sudo list.")
        return

    sudo_users = list(sudo_users_collection.find())
    if len(sudo_users) == 0:
        update.message.reply_text("No sudo users found.")
        return

    sudo_list = "\n".join([str(user["user_id"]) for user in sudo_users])
    update.message.reply_text(f"Sudo Users:\n{sudo_list}")

def send(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != OWNER_ID and not is_sudo_user(user_id):
        update.message.reply_text("You don't have permission to use this command.")
        return

    if len(context.args) < 2:
        update.message.reply_text("Usage: /send <user_id> <message>")
        return

    try:
        target_user_id = int(context.args[0])
        message = " ".join(context.args[1:])
        context.bot.send_message(chat_id=target_user_id, text=message)
        update.message.reply_text("Message sent successfully!")
    except ValueError:
        update.message.reply_text("Invalid user ID format.")
    except TelegramError as e:
        update.message.reply_text(f"Failed to send message: {e}")

def main():
    updater = Updater("7382235042:AAFv5nrAHJEnq3cuJUOTCGLKYdVDeIaYZnE", use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_EDIT_TYPE: [MessageHandler(Filters.text & ~Filters.command, ask_message_link)],
            ASK_MESSAGE_LINK: [MessageHandler(Filters.text & ~Filters.command, edit_message)],
            EDIT_MESSAGE: [MessageHandler((Filters.text | Filters.photo | Filters.document) & ~Filters.command, apply_edit)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("sudo", sudo))
    dp.add_handler(CommandHandler("rmsudo", rmsudo))
    dp.add_handler(CommandHandler("sudolist", sudolist))  # Added handler for /sudolist
    dp.add_handler(CommandHandler("send", send))          # Added handler for /send

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
