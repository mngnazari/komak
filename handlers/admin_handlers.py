from telegram import Update
from telegram.ext import ContextTypes
from database import is_admin, ADMIN_ID
from models import SessionLocal, Referral, User
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from datetime import datetime, timedelta
import secrets
import string
import logging

logger = logging.getLogger(__name__)

from telegram import Update
from telegram.ext import ContextTypes
from models import SessionLocal, Referral
from config import Config
import secrets
import string
from datetime import datetime, timedelta

# در handlers/admin_handlers.py
from utils import generate_referral_link


async def admin_generate_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        with SessionLocal() as db:
            # احراز هویت ادمین
            if not is_admin(user.id):
                await update.message.reply_text("❌ دسترسی غیرمجاز!")
                return

            # تولید کد منحصر به فرد
            code = f"ADMIN_{secrets.token_urlsafe(8)}"
            while db.query(Referral).filter_by(referral_code=code).first():
                code = f"ADMIN_{secrets.token_urlsafe(8)}"

            # ایجاد لینک دعوت
            bot = await context.bot.get_me()
            invite_link = generate_referral_link(bot.username, code)

            # ذخیره در دیتابیس
            new_ref = Referral(
                referrer_id=user.id,
                referral_code=code,
                expires_at=datetime.now() + timedelta(days=365),
                is_admin=True,
                usage_limit=-1  # نامحدود
            )

            db.add(new_ref)
            db.commit()

            # ارسال پیام
            msg = (
                "🔗 لینک دعوت ادمین:\n"
                f"{invite_link}\n"
                "⏳ اعتبار: 1 سال\n"
                "👥 تعداد استفاده: نامحدود"
            )
            await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"خطا: {str(e)}")
        await update.message.reply_text("❌ خطا در تولید لینک!")


async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = get_all_users()
    response = "👥 لیست کاربران:\n\n"
    for user in users:
        response += f"🆔 {user[0]} - 📞 {user[2]}\n"

    await update.message.reply_text(response)


from sqlalchemy.orm import aliased


def build_tree(root_id: int, db: Session, level: int = 0):
    """ساختار درختی دعوت‌ها را به صورت متن بازگشت می‌دهد"""
    try:
        Inviter = aliased(User)
        Invitee = aliased(User)

        # دریافت داده‌های سطح فعلی
        nodes = db.query(
            Inviter.id.label("inviter_id"),
            Inviter.full_name.label("inviter_name"),
            Invitee.id.label("invitee_id"),
            Invitee.full_name.label("invitee_name")
        ).join(
            Invitee, Invitee.inviter_id == Inviter.id
        ).filter(
            Inviter.id == root_id
        ).all()

        tree_str = ""
        prefix = "│   " * (level - 1) + "├── " if level > 0 else ""

        for node in nodes:
            # افزودن دعوت‌کننده فعلی
            tree_str += f"{prefix}👤 {node.inviter_name}\n"

            # بازگشت برای فرزندان
            tree_str += build_tree(node.invitee_id, db, level + 1)

        return tree_str

    except Exception as e:
        logger.error(f"خطا در ساخت درخت: {str(e)}")
        return "❌ خطا در نمایش ساختار"


# در handlers/admin_handlers.py
async def show_referral_tree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with SessionLocal() as db:
            # دریافت ادمین ریشه
            root_admin = db.query(User).filter(
                User.id == Config.ADMINS[0]
            ).first()

            if not root_admin:
                await update.message.reply_text("❌ ادمین اصلی یافت نشد!")
                return

            tree = build_tree(root_admin.id, db)
            await update.message.reply_text(f"🌳 ساختار دعوت‌ها:\n{tree}")

    except Exception as e:
        logger.error(f"خطا: {str(e)}")
        await update.message.reply_text("❌ خطا در نمایش درخت")
