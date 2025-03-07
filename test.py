from telegram import Update, ParseMode, InputMediaPhoto, InputMediaDocument
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
import re

OWNER_ID = 6663845789  # Your Telegram Owner ID
ASK_MESSAGE_LINK, EDIT_MESSAGE = range(2)

def start(update: Update, context: CallbackContext):
    """Handles /start command: Owner gets full access, others get DMCA info."""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        update.message.reply_text(
            "**DMCA Protection Bot**\n\n"
            "This bot helps remove **DMCA-infringing** and **NSFW** content.\n",
        )
        return
    
    update.message.reply_text(
    "**Owner Panel of Bot**\n"
    "➡️ `/send <chat\\_id | link> <message>` to send messages.\n"
    "➡️ `/edit` to edit messages in groups/channels.",
    parse_mode=ParseMode.MARKDOWN_V2
    )
    
def parse_message_link(link: str):
    """Extracts chat ID and message ID from Telegram message links."""
    public_match = re.match(r"https://t\.me/([\w\d_]+)/(\d+)", link)
    if public_match:
        return f"@{public_match.group(1)}", int(public_match.group(2))

    private_match = re.match(r"https://t\.me/c/(-?\d+)/(\d+)", link)
    if private_match:
        return int(private_match.group(1)), int(private_match.group(2))

    return None, None

def send(update: Update, context: CallbackContext):
    """Allows the owner to send messages to a group, channel, or user."""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        update.message.reply_text("❌ You don't have permission to use this command.")
        return

    if len(context.args) < 2:
        update.message.reply_text("⚠️ **Usage:** `/send <chat_link | chat_id> <message>`")
        return

    target_chat = context.args[0]
    message_text = " ".join(context.args[1:])

    # Convert public and private chat links to chat_id format
    public_match = re.match(r"https://t\.me/([\w\d_]+)", target_chat)
    private_match = re.match(r"https://t\.me/c/(\d+)", target_chat)

    if public_match:
        target_chat = f"@{public_match.group(1)}"
    elif private_match:
        target_chat = f"-100{private_match.group(1)}"

    try:
        context.bot.send_message(chat_id=target_chat, text=message_text, parse_mode=ParseMode.HTML)
        update.message.reply_text("✅ **Message sent successfully!**")
    except Exception as e:
        update.message.reply_text(f"❌ **Failed to send message:** {e}")

def ask_message_link(update: Update, context: CallbackContext) -> int:
    """Asks the user to provide a message link to edit."""
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        update.message.reply_text("❌ You don't have permission to use this command.")
        return ConversationHandler.END

    update.message.reply_text("🔗 **Send the message link of the group/channel to edit:**")
    return ASK_MESSAGE_LINK

def edit_message(update: Update, context: CallbackContext) -> int:
    """Processes the message link and asks for the new text/media."""
    message_link = update.message.text
    chat_id, message_id = parse_message_link(message_link)

    if not chat_id or not message_id:
        update.message.reply_text("❌ Invalid message link. Please provide a valid Telegram message link.")
        return ASK_MESSAGE_LINK

    context.user_data['chat_id'] = chat_id
    context.user_data['message_id'] = message_id

    update.message.reply_text("✍️ **Send the new text or media to update the message.**")
    return EDIT_MESSAGE

def apply_edit(update: Update, context: CallbackContext) -> int:
    """Applies the edit to the specified message in the group/channel."""
    chat_id = context.user_data.get('chat_id')
    message_id = context.user_data.get('message_id')

    try:
        if update.message.text:
            new_text = update.message.text
            context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=new_text, parse_mode=ParseMode.HTML
            )
            update.message.reply_text("✅ **Message updated successfully!**")
        elif update.message.photo:
            media = InputMediaPhoto(update.message.photo[-1].file_id)
            context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media)
            update.message.reply_text("✅ **Message photo updated successfully!**")
        elif update.message.document:
            media = InputMediaDocument(update.message.document.file_id)
            context.bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media)
            update.message.reply_text("✅ **Message document updated successfully!**")
        else:
            update.message.reply_text("⚠️ **Please send valid text or media to replace the message.**")
            return EDIT_MESSAGE

        return ConversationHandler.END
    except Exception as e:
        update.message.reply_text(f"❌ **Error:** {e}")
        return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels the edit operation."""
    update.message.reply_text("❌ **Edit operation cancelled.**")
    return ConversationHandler.END

def main():
    updater = Updater("7382235042:AAFv5nrAHJEnq3cuJUOTCGLKYdVDeIaYZnE", use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("edit", ask_message_link)],
        states={
            ASK_MESSAGE_LINK: [MessageHandler(Filters.text & ~Filters.command, edit_message)],
            EDIT_MESSAGE: [MessageHandler((Filters.text | Filters.photo | Filters.document) & ~Filters.command, apply_edit)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("send", send))
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
