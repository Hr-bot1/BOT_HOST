import os
import re
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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration (use environment variables for security)
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')  # Set in GitHub Secrets
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))     # Your Telegram user ID
WHITELIST = os.getenv('WHITELIST', '').split(',')      # Allowed domains (e.g., 'example.com,github.com')
DELETE_WARNING_AFTER = 10  # Seconds before deleting warning message

# Enhanced URL detection pattern
URL_PATTERN = re.compile(
    r'(https?://[^\s]+)|(www\.[^\s]+)|([^\s]+\.(com|net|org|io|co|xyz|me|info|ru|biz|online|site))',
    re.IGNORECASE
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Hello! I'm an advanced URL filter bot.\n\n"
        "🛡️ Add me to your group and I'll delete unwanted URLs.\n"
        "⚠️ Make sure to grant me admin privileges with 'Delete Messages' permission.\n\n"
        "Use /help to see available commands."
      	"Create BY @Termux_Team_BD ",
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when the command /help is issued."""
    help_text = (
        "🔗 *URL Filter Bot Help*\n\n"
        "- I automatically delete messages containing URLs from non-admin users\n"
        "- Group admins can still send URLs\n"
        f"- Whitelisted domains: {', '.join(WHITELIST) if WHITELIST else 'None'}\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/status - Check bot permissions\n"
        "/whitelist - Show allowed domains"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status and permissions in a group."""
    chat = update.effective_chat
    
    if chat.type == 'private':
        await update.message.reply_text("⚠️ This command only works in groups.")
        return
    
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        if bot_member.status == 'administrator':
            if bot_member.can_delete_messages:
                await update.message.reply_text("✅ Bot is properly configured as admin with delete messages permission.")
            else:
                await update.message.reply_text("❌ Bot is admin but DOESN'T have permission to delete messages.")
        else:
            await update.message.reply_text("❌ Bot is NOT an admin. Please make me an admin with 'Delete Messages' permission.")
    except Exception as e:
        logger.error(f"Error checking bot status: {e}")
        await update.message.reply_text("❌ Error checking bot status.")

async def show_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show currently whitelisted domains."""
    if WHITELIST:
        await update.message.reply_text(
            f"✅ Whitelisted domains:\n{', '.join(WHITELIST)}"
        )
    else:
        await update.message.reply_text("ℹ️ No domains are currently whitelisted.")

async def delete_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filter messages containing URLs from non-admin users."""
    try:
        message = update.message
        chat = update.effective_chat
        user = update.effective_user
        
        # Skip processing in private chats or if message is from admin
        if chat.type == 'private' or user.id == ADMIN_ID:
            return
        
        # Check if message contains URL
        if message.text and URL_PATTERN.search(message.text):
            # Check if URL is in whitelist
            if WHITELIST and any(domain.lower() in message.text.lower() for domain in WHITELIST):
                return
            
            # Check if user is admin
            chat_member = await context.bot.get_chat_member(chat.id, user.id)
            is_admin = chat_member.status in ['administrator', 'creator']
            
            if not is_admin:
                try:
                    # Delete the message
                    await message.delete()
                    
                    # Send warning that will auto-delete
                    warning = await context.bot.send_message(
                        chat_id=chat.id,
                        text=f"⚠️ {user.mention_html()}, URLs are not allowed for non-admin users.",
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Schedule warning deletion
                    context.job_queue.run_once(
                        delete_warning,
                        DELETE_WARNING_AFTER,
                        data={'chat_id': chat.id, 'message_id': warning.message_id}
                    )
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
    except Exception as e:
        logger.error(f"Error in message handler: {e}")

async def delete_warning(context: CallbackContext):
    """Delete the warning message after delay."""
    job = context.job
    try:
        await context.bot.delete_message(
            chat_id=job.data['chat_id'],
            message_id=job.data['message_id']
        )
    except Exception as e:
        logger.error(f"Error deleting warning message: {e}")

def main():
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("whitelist", show_whitelist))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_url))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
