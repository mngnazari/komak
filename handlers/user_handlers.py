from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)
from keyboards import customer_kb
import database
from keyboards import admin_kb, customer_kb
from models import SessionLocal, User, Referral, Wallet
from sqlalchemy.exc import SQLAlchemyError
from database import add_user, validate_referral, is_admin
from config import Config
import logging
import secrets  # این خط را اضافه کنید
from datetime import datetime, timedelta

# بقیه ایمپورت‌ها...
logger = logging.getLogger(__name__)


import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)

# تنظیم فرمت لاگ‌های JSON
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'
)
# تنظیم سطح لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
ADMIN_ID = 2138687434
FULL_NAME, PHONE = range(2)

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

from models import User, Wallet, SessionLocal
from config import Config
from database import validate_referral
from keyboards import admin_kb, customer_kb

logger = logging.getLogger(__name__)

# مراحل گفتگو
FULL_NAME, PHONE = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اولین نقطه تماس کاربر با بات"""
    user = update.effective_user
    try:
        with SessionLocal() as db:
            # ==================== بخش مدیریت ادمین ====================
            if user.id in Config.ADMINS:
                admin = db.query(User).get(user.id)

                # اگر ادمین وجود نداشت، آن را ایجاد کنید
                if not admin:
                    try:
                        new_admin = User(
                            id=user.id,
                            full_name=user.full_name or "ادمین سیستم",
                            phone=f"admin_{user.id}",  # شماره منحصر به فرد
                            is_admin=True,
                            remaining_invites=0,
                            inviter_id=None
                        )
                        db.add(new_admin)

                        # ایجاد کیف پول برای ادمین
                        wallet = Wallet(user_id=user.id)
                        db.add(wallet)

                        db.commit()
                        logger.info(f"✅ ادمین جدید ایجاد شد: {user.id}")

                    except IntegrityError as e:
                        db.rollback()
                        logger.error(f"خطای یکتایی در ایجاد ادمین: {str(e)}")
                        await update.message.reply_text("❌ خطا در ایجاد حساب ادمین!")
                        return ConversationHandler.END

                await update.message.reply_text(
                    "👑 به پنل مدیریتی خوش آمدید!",
                    reply_markup=admin_kb
                )
                return ConversationHandler.END

            # ==================== بخش کاربران عادی ====================
            # بررسی آیا کاربر قبلاً ثبت نام کرده
            existing_user = db.query(User).get(user.id)
            if existing_user:
                await update.message.reply_text(
                    "✅ قبلاً ثبت نام کرده‌اید!",
                    reply_markup=customer_kb
                )
                return ConversationHandler.END

            # استخراج کد دعوت از آرگومان‌ها
            referral_code = None
            if context.args:
                for arg in context.args:
                    if arg.startswith("ref_"):
                        referral_code = arg[4:]
                        break

            if not referral_code:
                await update.message.reply_text(
                    "🔒 دسترسی فقط از طریق لینک دعوت ممکن است!\n\n"
                    "⚠️ لطفاً از لینک معتبر استفاده کنید."
                )
                return ConversationHandler.END

            # اعتبارسنجی کد دعوت
            valid, referrer_id = validate_referral(db, referral_code)
            if not valid:
                await update.message.reply_text(f"❌ {referrer_id}")
                return ConversationHandler.END

            # ذخیره اطلاعات موقت
            context.user_data.clear()
            context.user_data.update({
                "referral_code": referral_code,
                "referrer_id": referrer_id
            })

            await update.message.reply_text(
                "👤 لطفاً نام کامل خود را وارد کنید:",
                reply_markup=ReplyKeyboardRemove()
            )
            return FULL_NAME

    except Exception as e:
        logger.error(f"🔥 خطای شدید در شروع: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "⚠️ خطای موقت سیستم!\n"
            "لطفاً با پشتیبانی تماس بگیرید یا چند دقیقه دیگر تلاش کنید."
        )
        return ConversationHandler.END

async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text
    await update.message.reply_text(
        "📱 لطفاً شماره تماس خود را ارسال کنید:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("ارسال شماره 📲", request_contact=True)]],
            resize_keyboard=True
        )
    )
    return PHONE


# فایل: handlers/user_handlers.py
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        with SessionLocal() as db:
            # دریافت اطلاعات از context
            full_name = context.user_data["full_name"]
            phone = update.message.contact.phone_number if update.message.contact else update.message.text
            referral_code = context.user_data["referral_code"]

            # اعتبارسنجی کد
            valid, referrer_id = validate_referral(db, referral_code)
            if not valid:
                await update.message.reply_text(f"❌ {referrer_id}")
                return ConversationHandler.END

            # ایجاد کاربر جدید
            new_user = User(
                id=user.id,
                full_name=full_name,
                phone=phone,
                inviter_id=referrer_id,
                remaining_invites=5
            )

            db.add(new_user)
            db.commit()

            # ثبت در لیست مدعوین
            invited_user = InvitedUser(
                referrer_id=referrer_id,
                invited_user_id=user.id,
                invited_full_name=full_name,
                invited_phone=phone,
                invited_at=datetime.now()
            )

            db.add(invited_user)
            db.commit()

            await update.message.reply_text(
                "✅ ثبت نام موفق! از منوی زیر استفاده کنید:",
                reply_markup=customer_kb
            )

    except IntegrityError:
        await update.message.reply_text("❌ شماره تلفن تکراری است!")
    except Exception as e:
        logger.error(f"خطای ثبت نام: {str(e)}")
        await update.message.reply_text("❌ خطای سیستمی!")
    finally:
        context.user_data.clear()
        return ConversationHandler.END


async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text
    await update.message.reply_text(
        "📱 لطفاً شماره تماس خود را ارسال کنید:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("ارسال شماره 📲", request_contact=True)]],
            resize_keyboard=True
        )
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        with SessionLocal() as db:
            # دریافت شماره تماس
            phone = (
                update.message.contact.phone_number
                if update.message.contact
                else update.message.text.strip()
            )

            # فرمت‌دهی شماره ایران
            if not phone.startswith('+'):
                phone = f"+98{phone[-10:]}"  # تبدیل به فرمت بین‌المللی

            # دریافت کد رفرال از context
            referral_code = context.user_data.get("referral_code")
            referrer_id = None

            # اعتبارسنجی کد رفرال
            if referral_code:
                valid, result = validate_referral(db, referral_code)
                if valid:
                    referrer_id = result
                else:
                    await update.message.reply_text(f"❌ {result}")
                    return ConversationHandler.END

            # ایجاد کاربر جدید
            user_data = {
                'id': user.id,
                'full_name': context.user_data["full_name"],
                'phone': phone,
                'inviter_id': referrer_id,
                'is_admin': False,
                'remaining_invites': 5  # مقدار پیش‌فرض
            }

            if add_user(user_data):
                # کاهش تعداد دعوت‌های باقی‌مانده دعوت‌کننده
                if referrer_id:
                    referrer = db.query(User).get(referrer_id)
                    if referrer and not referrer.is_admin:
                        referrer.remaining_invites -= 1
                        db.commit()

                # ارسال کیبورد مشتری
                await update.message.reply_text(
                    "✅ ثبت نام موفق! لطفاً از منوی زیر استفاده کنید:",
                    reply_markup=customer_kb
                )
            else:
                await update.message.reply_text("❌ خطا در ثبت اطلاعات!")

    except Exception as e:
        logger.error(f"خطای سیستمی: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطای سیستمی! لطفاً مجدداً تلاش کنید.")

    finally:
        context.user_data.clear()
        return ConversationHandler.END


# فایل: handlers/user_handlers.py
async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ ثبت نام لغو شد.")
    return ConversationHandler.END


# اصلاح بخش پایانی فایل
start_conversation = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
        PHONE: [MessageHandler(filters.CONTACT | filters.TEXT & ~filters.COMMAND, get_phone)]
    },
    fallbacks=[CommandHandler("cancel", cancel_registration)]
)




async def show_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "بازه زمانی مورد نظر را انتخاب کنید:",
        reply_markup=archive_reply_kb
    )


async def handle_active_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    active_orders = database.get_active_orders(user.id)

    if not active_orders:
        await update.message.reply_text("✅ هیچ سفارش فعالی ندارید!")
        return

    response = "📋 سفارشات فعال شما:\n\n"
    for order in active_orders:
        response += f"""🔖 شماره سفارش: {order[0]}
📁 فایل: {order[2]}
🧮 تعداد: {order[7]}
⏳ وضعیت: {order[9]}
➖➖➖➖➖➖➖\n"""

    await update.message.reply_text(response)




async def handle_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    days = None
    if text == "🕒 هفته اخیر":
        days = 7
    elif text == "📅 ماه اخیر":
        days = 30

    files = database.get_files_by_user(user.id, days)

    if not files:
        await update.message.reply_text(
            "❌ هیچ فایلی در این بازه زمانی یافت نشد!",
            reply_markup=customer_kb
        )
        return

    for file in files:
        miladi_date = datetime.strptime(file[6], "%Y-%m-%d %H:%M:%S")
        shamsi_date = jdatetime.fromgregorian(datetime=miladi_date)

        caption = f"""
📁 نام فایل: {file[2]}
📅 تاریخ ارسال: 
  شمسی: {shamsi_date.strftime("%Y/%m/%d")}
  میلادی: {miladi_date.strftime("%Y/%m/%d")}
🧮 تعداد: {file[7]}
📝 توضیحات: {file[8]}
        """.strip()

        await context.bot.send_document(
            chat_id=user.id,
            document=file[4],
            caption=caption
        )

    await update.message.reply_text(
        "✅ فایل‌های شما ارسال شدند!",
        reply_markup=customer_kb
    )


async def generate_user_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تولید لینک دعوت برای کاربران عادی"""
    user = update.effective_user
    try:
        with SessionLocal() as db:
            # دریافت اطلاعات کاربر از دیتابیس
            db_user = db.query(User).get(user.id)

            if not db_user:
                await update.message.reply_text("❌ کاربر یافت نشد! لطفاً ابتدا ثبت نام کنید.")
                return

            # بررسی تعداد دعوت‌های باقی‌مانده
            if db_user.remaining_invites <= 0:
                await update.message.reply_text(
                    "⚠️ تعداد دعوت‌های شما به اتمام رسیده!\n"
                    "🎉 برای دریافت دعوت بیشتر میتوانید از سیستم هدیه استفاده کنید."
                )
                return

            # تولید کد دعوت یکتا
            code = None
            attempts = 0
            max_attempts = 5

            while attempts < max_attempts:
                try:
                    code = f"USER_{secrets.token_urlsafe(8)}"  # استفاده صحیح از secrets
                    new_ref = Referral(
                        referrer_id=user.id,
                        referral_code=code,
                        expires_at=datetime.now() + timedelta(days=30),
                        max_uses=1,
                        is_admin=False  # استفاده از نام صحیح فیلد
                    )
                    db.add(new_ref)
                    db_user.remaining_invites -= 1
                    db.commit()
                    break
                except IntegrityError:
                    db.rollback()
                    attempts += 1
                    logger.warning(f"تلاش مجدد برای تولید کد. تلاش شماره: {attempts}")

            if not code:
                logger.error("عدم توانایی در تولید کد پس از 5 تلاش")
                await update.message.reply_text("❌ خطا در تولید کد! لطفاً بعداً تلاش کنید.")
                return

            # ساخت لینک دعوت
            bot = await context.bot.get_me()
            invite_link = f"https://t.me/{bot.username}?start=ref_{code}"

            response = (
                "🎉 لینک دعوت شما:\n\n"
                f"{invite_link}\n\n"
                "📝 مشخصات:\n"
                f"• اعتبار: 30 روز\n"
                f"• تعداد استفاده باقی‌مانده: {db_user.remaining_invites}/5\n"
                "• یکبار مصرف"
            )

            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"خطای تولید لینک: {str(e)}", exc_info=True)
        await update.message.reply_text(
            "⚠️ خطای موقت سیستم!\n"
            "لطفاً چند دقیقه دیگر مجدداً تلاش کنید."
        )


async def handle_gift_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        with SessionLocal() as db:
            # بررسی شرایط دریافت هدیه
            user_data = db.query(User).get(user.id)

            # بررسی وجود کاربر در دیتابیس
            if not user_data:
                await update.message.reply_text("❌ کاربر یافت نشد!")
                return

            # بررسی شرایط هدیه
            if meets_gift_conditions(db, user.id):
                # افزودن اعتبار به کیف پول
                wallet = db.query(Wallet).get(user.id)
                if wallet:
                    wallet.discount += 100  # افزودن 100 واحد اعتبار
                    db.commit()
                    await update.message.reply_text("🎉 100 واحد اعتبار هدیه دریافت کردید!")
                else:
                    await update.message.reply_text("❌ کیف پول یافت نشد!")
            else:
                await update.message.reply_text("⚠️ شرایط دریافت هدیه را ندارید!")

    except Exception as e:
        logger.error(f"خطا در پردازش درخواست هدیه: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطای سیستمی! لطفاً مجدداً تلاش کنید.")


# user_handlers.py
# فایل handlers/user_handlers.py
async def show_direct_invites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        invites = database.get_direct_invites(user.id)

        if not invites:
            await update.message.reply_text("ℹ️ هنوز کسی را دعوت نکرده‌اید!")
            return

        response = "📋 لیست مدعوین مستقیم شما:\n\n"
        for idx, invite in enumerate(invites, 1):
            response += (
                f"{idx}. 👤 {invite['invited_full_name']}\n"
                f"   📞 {invite['invited_phone']}\n"
                f"   📅 {invite['invited_date']}\n\n"
            )

        await update.message.reply_text(response)

    except Exception as e:
        logging.error(f"خطا در نمایش مدعوین: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطای سیستمی!")

