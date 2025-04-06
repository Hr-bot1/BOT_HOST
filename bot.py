import os
import re
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))
WHITELIST = os.getenv('WHITELIST', '').split(',')
RESTRICT_SECONDS = 3  # Restrict user for 3 seconds
CREATOR_CHANNEL = "https://t.me/Termux_Team_BD"

# URL detection pattern
URL_PATTERN = re.compile(
    r'https?://\S+|www\.\S+|\S+\.(com|net|org|io|co|xyz|me|info|ru|biz|online|site)\b',
    re.IGNORECASE
)

async def restrict_user(chat_id, user_id, context, seconds):
    """Restrict user from sending messages temporarily"""
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            ),
            until_date=int(time.time()) + seconds
        )
    except BadRequest as e:
        logger.error(f"Failed to restrict user: {e}")

async def delete_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle URL messages from non-admins"""
    try:
        message = update.message
        chat = update.effective_chat
        user = update.effective_user

        # Skip if from admin or in private chat
        if chat.type == 'private' or user.id == ADMIN_ID or user.is_bot:
            return

        # Check for URLs
        text = message.text or message.caption or ""
        if not URL_PATTERN.search(text):
            return

        # Check whitelist
        if WHITELIST and any(domain.lower() in text.lower() for domain in WHITELIST if domain.strip()):
            return

        try:
            # Delete the URL message
            await message.delete()
            
            # Restrict user for 3 seconds
            await restrict_user(chat.id, user.id, context, RESTRICT_SECONDS)
            
            # Send warning
            warning = await context.bot.send_message(
                chat_id=chat.id,
                text=f"⚠️ {user.mention_html()}, URLs are not allowed! (Restricted for {RESTRICT_SECONDS}s)",
                parse_mode=ParseMode.HTML
            )
            
            # Delete warning after delay
            await asyncio.sleep(5)
            await warning.delete()

        except Exception as e:
            logger.error(f"Error handling URL: {e}")

    except Exception as e:
        logger.error(f"Error in message handler: {e}")

# [Keep all other functions (start, help_command, etc.) the same as in your original code]

def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("whitelist", show_whitelist))
    
    # Handle all messages that might contain URLs
    application.add_handler(MessageHandler(
        filters.TEXT | filters.CAPTION | filters.PHOTO | filters.VIDEO,
        delete_url
    ))

    application.run_polling()

if __name__ == '__main__':
    main()
