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


async def admin_generate_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        with SessionLocal() as db:
            if not is_admin(user.id):
                await update.message.reply_text("❌ دسترسی غیرمجاز!")
                return

            code = None
            attempts = 0
            while not code and attempts < 10:
                try:
                    code = f"ADMIN_{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))}"
                    new_referral = Referral(
                        referrer_id=user.id,
                        referral_code=code,
                        is_admin=True,
                        expires_at=datetime.now() + timedelta(days=365)
                    )
                    db.add(new_referral)
                    db.commit()

                    await update.message.reply_text(
                        f"✅ کد دعوت ادمین ایجاد شد:\n`{code}`",
                        parse_mode="Markdown"
                    )
                    return

                except IntegrityError:
                    db.rollback()
                    code = None
                    attempts += 1

            await update.message.reply_text("❌ خطا در تولید کد دعوت")

    except Exception as e:
        logger.error(f"خطا در تولید کد دعوت: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطای سیستمی!")


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
