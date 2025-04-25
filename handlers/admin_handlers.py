from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.exc import IntegrityError
import logging
from datetime import datetime, timedelta
import secrets
import string

from models import SessionLocal, User, Referral
from config import Config
from database import create_referral
from sqlalchemy.orm import Session
from models import SessionLocal, User, Referral
from config import Config

logger = logging.getLogger(__name__)


async def admin_generate_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        with SessionLocal() as db:
            # بررسی مجوز ادمین
            admin = db.query(User).get(user.id)
            if not admin or not admin.is_admin:
                await update.message.reply_text("❌ دسترسی غیرمجاز!")
                return

            # تولید کد دعوت ادمین
            code, error = create_referral(db, user.id, is_admin=True)

            if error:
                logger.error(f"خطا در تولید کد ادمین: {error}")
                await update.message.reply_text("❌ خطا در تولید کد!")
                return

            # ساخت لینک دعوت
            bot = await context.bot.get_me()
            invite_link = f"https://t.me/{bot.username}?start=ref_{code}"

            await update.message.reply_text(
                f"🎉 لینک دعوت ادمین با موفقیت ایجاد شد!\n\n"
                f"🔗 لینک: {invite_link}\n"
                "⚙️ ویژگی‌ها:\n"
                "- تعداد استفاده: نامحدود\n"
                "- اعتبار: دائمی\n"
                "- جایزه هر دعوت: 50 دلار"
            )

    except IntegrityError as e:
        logger.error(f"خطای یکتایی: {str(e)}")
        await update.message.reply_text("⚠️ کد تکراری! لطفاً مجدد تلاش کنید.")
    except Exception as e:
        logger.error(f"خطای سیستمی: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطای غیرمنتظره! لطفاً لاگ‌ها را بررسی کنید.")

async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = get_all_users()
    response = "👥 لیست کاربران:\n\n"
    for user in users:
        response += f"🆔 {user[0]} - 📞 {user[2]}\n"

    await update.message.reply_text(response)


from sqlalchemy.orm import aliased

from sqlalchemy.orm import Session  # اضافه کردن این خط
from models import SessionLocal  # اطمینان از وجود این ایمپورت

# اصلاح تابع build_tree
def build_tree(root_id: int, db: Session, level: int = 0):
    async def show_referral_tree(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش درخت دعوت با ساختار سلسله مراتبی"""
        try:
            with SessionLocal() as db:
                # دریافت کاربر ریشه (ادمین اصلی)
                root_user = db.query(User).filter(
                    User.id == Config.ADMINS[0]
                ).first()

                if not root_user:
                    await update.message.reply_text("❌ ادمین اصلی یافت نشد!")
                    return

                # ساخت درخت با الگوریتم بازگشتی
                def build_tree(user_id: int, level: int = 0):
                    branches = []
                    current_user = db.query(User).get(user_id)

                    # افزودن کاربر فعلی
                    prefix = "│   " * (level - 1) + "├── " if level > 0 else ""
                    branches.append(f"{prefix}👤 {current_user.full_name} (ID: {current_user.id})")

                    # بازگشت برای فرزندان
                    children = db.query(User).filter(User.inviter_id == user_id).all()
                    for child in children:
                        branches.extend(build_tree(child.id, level + 1))

                    return branches

                # ساختار نهایی
                tree = "\n".join(build_tree(root_user.id))

                await update.message.reply_text(
                    f"🌳 ساختار سلسله مراتبی:\n\n{tree}",
                    parse_mode="HTML"
                )

        except Exception as e:
            logger.error(f"خطا در نمایش درخت: {str(e)}", exc_info=True)
            await update.message.reply_text("❌ خطا در ایجاد ساختار درختی")


async def show_referral_tree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش ساختار سلسله مراتبی دعوت‌ها"""
    try:
        with SessionLocal() as db:
            # دریافت کاربر ریشه (اولین ادمین)
            root_admin = db.query(User).filter(
                User.id == Config.ADMINS[0]
            ).first()

            if not root_admin:
                await update.message.reply_text("❌ ادمین اصلی یافت نشد!")
                return

            # ساخت درخت با کوئری بازگشتی
            Inviter = aliased(User)
            Invitee = aliased(User)

            query = db.query(
                Inviter.id.label("inviter_id"),
                Inviter.full_name.label("inviter_name"),
                Invitee.id.label("invitee_id"),
                Invitee.full_name.label("invitee_name")
            ).join(
                Invitee, Invitee.inviter_id == Inviter.id
            ).filter(
                Inviter.id == Config.ADMINS[0]
            )

            tree = {}
            for row in query.all():
                tree.setdefault(row.inviter_id, []).append({
                    "invitee_id": row.invitee_id,
                    "invitee_name": row.invitee_name
                })

            # ساخت متن قابل نمایش
            def build_branch(parent_id, level=0):
                branch = []
                prefix = "│   " * (level - 1) + "├── " if level > 0 else ""

                if parent_id in tree:
                    for child in tree[parent_id]:
                        branch.append(f"{prefix}👤 {child['invitee_name']} (ID: {child['invitee_id']})")
                        branch.extend(build_branch(child['invitee_id'], level + 1))

                return branch

            result = ["🌳 ساختار دعوت‌ها:\n"]
            result.extend(build_branch(Config.ADMINS[0]))

            await update.message.reply_text("\n".join(result))

    except Exception as e:
        logger.error(f"خطا در نمایش درخت: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطا در ایجاد ساختار درختی")