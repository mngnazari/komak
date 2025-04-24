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


async def show_referral_tree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with SessionLocal() as db:
            if not is_admin(update.effective_user.id):
                await update.message.reply_text("❌ دسترسی غیرمجاز!")
                return

            Inviter = aliased(User)
            Invitee = aliased(User)

            tree = db.query(
                Inviter.id.label("inviter_id"),
                Inviter.full_name.label("inviter_name"),
                Invitee.id.label("invitee_id"),
                Invitee.full_name.label("invitee_name")
            ).join(
                Invitee, Invitee.inviter_id == Inviter.id
            ).filter(
                Inviter.inviter_id == None
            ).all()

            if not tree:
                await update.message.reply_text("ℹ️ هیچ ساختار دعوتی وجود ندارد")
                return

            tree_dict = {}
            for row in tree:
                if row.inviter_id not in tree_dict:
                    tree_dict[row.inviter_id] = {
                        "name": row.inviter_name,
                        "children": []
                    }
                tree_dict[row.inviter_id]["children"].append({
                    "id": row.invitee_id,
                    "name": row.invitee_name
                })

            def build_tree(branch, level=0):
                result = ""
                prefix = "│   " * (level - 1) + "├── " if level > 0 else ""
                result += f"{prefix}👤 {branch['name']}\n"
                for child in branch['children']:
                    result += build_tree(tree_dict.get(child["id"], {"name": child["name"], "children": []}), level + 1)
                return result

            root_id = update.effective_user.id
            root = tree_dict.get(root_id)
            if not root:
                await update.message.reply_text("🔍 ساختار دعوت برای شما یافت نشد.")
                return

            formatted_tree = build_tree(root)
            await update.message.reply_text(f"🌳 ساختار درختی دعوت‌ها:\n\n{formatted_tree}")

    except Exception as e:
        logger.error(f"خطا در نمایش درخت دعوت: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطای سیستمی!")
