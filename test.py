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
    """Check if the user is a sudo user."""
    return sudo_users_collection.find_one({"user_id": user_id}) is not None


async def start(update: Update, context: CallbackContext) -> int:
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
    """Grant sudo access."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("Only the bot owner can grant sudo access.")
        return

    if context.args:
        try:
            user_id = int(context.args[0])
            if sudo_users_collection.find_one({"user_id": user_id}):
                update.message.reply_text("User already has sudo access.")
            else:
                sudo_users_collection.insert_one({"user_id": user_id, "name": update.message.reply_to_message.from_user.first_name})
                update.message.reply_text(f"Sudo access granted to user {user_id}.")
        except ValueError:
            update.message.reply_text("Invalid user ID format.")
    else:
        update.message.reply_text("Usage: /sudo <user_id>")


def rmsudo(update: Update, context: CallbackContext):
    """Revoke sudo access."""
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


def sudolist(update: Update, context: CallbackContext):
    """Show the list of sudo users."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("Only the bot owner can view the sudo list.")
        return

    sudo_users = sudo_users_collection.find()
    if sudo_users.count() == 0:
        update.message.reply_text("No sudo users found.")
    else:
        sudo_list = "Sudo Users:\n\n"
        for user in sudo_users:
            sudo_list += f"Name: {user.get('name', 'Unknown')}\nUser ID: {user['user_id']}\n\n"
        update.message.reply_text(sudo_list)


def send_message(update: Update, context: CallbackContext):
    """Send a message to a specific chat."""
    user_id = update.effective_user.id

    if user_id != OWNER_ID and not is_sudo_user(user_id):
        update.message.reply_text("You don't have permission to use this command.")
        return

    if len(context.args) < 2:
        update.message.reply_text("Usage: /send <message> <group_username/chat_id/group_link>")
        return

    message_text = " ".join(context.args[:-1])
    group_identifier = context.args[-1]

    chat_id = None
    if group_identifier.isdigit() or (group_identifier[1:].isdigit() and group_identifier.startswith('-')):
        chat_id = int(group_identifier)
    elif group_identifier.startswith('@'):
        chat_id = group_identifier
    else:
        match = re.match(r"https://t\.me/([\w\d_]+)", group_identifier)
        if match:
            chat_id = f"@{match.group(1)}"

    if not chat_id:
        update.message.reply_text("Invalid group identifier. Please provide a valid chat ID, username, or link.")
        return

    try:
        context.bot.send_message(chat_id=chat_id, text=message_text)
        update.message.reply_text("Message sent successfully!")
    except TelegramError as e:
        update.message.reply_text(f"Failed to send the message: {e}")


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
    dp.add_handler(CommandHandler("sudolist", sudolist))
    dp.add_handler(CommandHandler("send", send_message))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
