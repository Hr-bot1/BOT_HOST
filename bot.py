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
WHITELIST = os.getenv('WHITELIST', '').split(',')      # Allowed domains
DELETE_WARNING_AFTER = 10  # Seconds before deleting warning message
CREATOR_CHANNEL = "https://t.me/Termux_Team_BD"  # Your channel link

# Enhanced URL detection pattern
URL_PATTERN = re.compile(
    r'(https?://[^\s]+)|(www\.[^\s]+)|([^\s]+\.(com|net|org|io|co|xyz|me|info|ru|biz|online|site))',
    re.IGNORECASE
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued."""
    welcome_text = f"""
🌟 <b>Welcome to Advanced URL Filter Bot!</b> 🌟

🛡️ <i>Protecting your group from unwanted links</i>

⚙️ <b>Features:</b>
✅ Auto-deletes URLs from non-admins
🔐 Whitelist allowed domains
⚡ Smart URL detection
👮 Admin-only URL privileges

🔧 <b>Setup:</b>
1. Add me to your group
2. Make me admin (with delete permission)
3. I'll handle the rest!

📢 <b>Note:</b> This bot is created by <a href="{CREATOR_CHANNEL}">Termux Team BD</a>
    """
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when the command /help is issued."""
    help_text = f"""
🔍 <b>URL Filter Bot Help</b> 🔍

📜 <b>Functionality:</b>
- Automatically deletes URLs from regular users
- Admins can post any links
- Whitelist system for allowed domains

🛠️ <b>Commands:</b>
/start - Show welcome message
/help - Display this help
/status - Check bot permissions
/whitelist - Show allowed domains

🌐 <b>Whitelisted Domains:</b>
{', '.join(WHITELIST) if WHITELIST else 'None currently'}

📢 <i>Maintained by <a href="{CREATOR_CHANNEL}">Termux Team BD</a></i>
    """
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status and permissions in a group."""
    chat = update.effective_chat
    
    if chat.type == 'private':
        await update.message.reply_text("⚠️ This command only works in groups.")
        return
    
    try:
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        status_icon = "✅" if bot_member.status == 'administrator' else "❌"
        delete_icon = "✅" if (bot_member.status == 'administrator' and bot_member.can_delete_messages) else "❌"
        
        status_text = f"""
🔧 <b>Bot Status Report</b> 🔧

{status_icon} <b>Admin Status:</b> {'Yes' if bot_member.status == 'administrator' else 'No'}
{delete_icon} <b>Delete Permission:</b> {'Enabled' if (bot_member.status == 'administrator' and bot_member.can_delete_messages) else 'Disabled'}

💡 <i>To fix issues:</i>
1. Make me admin
2. Enable 'Delete Messages' permission
        """
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error checking bot status: {e}")
        await update.message.reply_text("❌ Error checking bot status.")

async def show_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show currently whitelisted domains."""
    if WHITELIST:
        domains = "\n".join([f"🔹 {domain}" for domain in WHITELIST])
        message = f"""
✅ <b>Whitelisted Domains</b> ✅

These websites can be shared by anyone:

{domains}
        """
    else:
        message = "ℹ️ No domains are currently whitelisted."
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML
    )

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
                    
                    # Send stylish warning
                    warning = await context.bot.send_message(
                        chat_id=chat.id,
                        text=f"""
⚠️ <b>URL Alert!</b> ⚠️

{user.mention_html()}, URLs are restricted to admins only.

<i>This warning will self-destruct in {DELETE_WARNING_AFTER} seconds...</i>
                        """,
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
