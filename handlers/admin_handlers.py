from telegram import Update
from telegram.ext import ContextTypes
import database
from config import Config
from database import create_referral, is_admin

from config import Config
from database import create_referral, is_admin
import logging
logger = logging.getLogger(__name__)

async def admin_generate_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        if not is_admin(user.id):
            await update.message.reply_text("❌ دسترسی غیرمجاز!")
            return

        code = create_referral(user.id, is_admin=True)
        await update.message.reply_text(
            f"✅ کد دعوت ادمین ایجاد شد:\n`{code}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطا: {str(e)}")
        await update.message.reply_text("❌ خطا در تولید کد دعوت")


async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != database.ADMIN_ID:
        return

    users = database.get_all_users()

    response = "👥 لیست کاربران:\n\n"
    for user in users:
        response += f"🆔 {user[0]} - 📞 {user[2]}\n"

    await update.message.reply_text(response)


async def show_referral_tree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != database.ADMIN_ID:
        return

    try:
        tree_data = database.get_referral_tree(database.ADMIN_ID)
        if not tree_data:
            await update.message.reply_text("ℹ️ هیچ ساختار دعوتی وجود ندارد.")
            return

        formatted_tree = database.format_referral_tree(tree_data)

        # ارسال به صورت کد برای حفظ فرمت
        await update.message.reply_text(
            f"🌳 ساختار درختی دعوت‌ها:\n\n"
            f"<code>{formatted_tree}</code>",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"خطا: {str(e)}")
        await update.message.reply_text("❌ خطا در نمایش درخت دعوت")