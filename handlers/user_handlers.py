from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)

import database
from keyboards import admin_kb, customer_kb
from models import SessionLocal, User, Referral
from sqlalchemy.exc import SQLAlchemyError
from database import add_user, validate_referral, is_admin
from config import Config
import logging
logger = logging.getLogger(__name__)

# تنظیم سطح لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
ADMIN_ID = 2138687434
FULL_NAME, PHONE = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        with SessionLocal() as db:
            # بررسی اول: آیا کاربر در لیست ادمین‌های config است؟
            if user.id in Config.ADMINS:
                db_admin = db.query(User).get(user.id)

                if not db_admin:
                    # ایجاد رکورد ادمین اگر وجود ندارد
                    admin_data = {
                        'id': user.id,
                        'full_name': user.full_name or "ادمین سیستم",
                        'phone': "بدون شماره",
                        'is_admin': True
                    }

                    if add_user(admin_data):
                        await update.message.reply_text(
                            "👑 پنل مدیریتی فعال شد!",
                            reply_markup=admin_kb
                        )
                    else:
                        await update.message.reply_text("❌ خطا در ایجاد حساب ادمین")
                    return ConversationHandler.END
                else:
                    # به روزرسانی اطلاعات ادمین اگر تغییر کرده
                    if db_admin.full_name != user.full_name:
                        db_admin.full_name = user.full_name
                        db.commit()

                    await update.message.reply_text(
                        "👑 پنل مدیریتی فعال شد!",
                        reply_markup=admin_kb
                    )
                    return ConversationHandler.END

            # منطق برای کاربران عادی
            db_user = db.query(User).get(user.id)

            if db_user:
                await update.message.reply_text(
                    "✅ قبلاً ثبت نام کرده‌اید!",
                    reply_markup=customer_kb
                )
                return ConversationHandler.END

            # استخراج کد دعوت از آرگومان‌ها
            referral_code = None
            if context.args:
                first_arg = context.args[0]
                if first_arg.startswith("ref_"):
                    referral_code = first_arg[4:]

            if not referral_code:
                await update.message.reply_text("🔒 دسترسی فقط از طریق لینک دعوت ممکن است!")
                return ConversationHandler.END

            # اعتبارسنجی کد دعوت
            valid, referrer_id = validate_referral(db, referral_code)
            if not valid:
                await update.message.reply_text(f"❌ {referrer_id}")
                return ConversationHandler.END

            context.user_data["referral_code"] = referral_code
            context.user_data["referrer_id"] = referrer_id

            await update.message.reply_text("👤 لطفاً نام کامل خود را وارد کنید:")
            return FULL_NAME

    except Exception as e:
        logger.error(f"خطای سیستمی: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطای سیستمی! لطفاً مجدداً تلاش کنید.")
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
    try:
        with SessionLocal() as db:
            # استخراج اطلاعات از context
            phone = (
                update.message.contact.phone_number
                if update.message.contact
                else update.message.text.strip()
            )

            user_data = {
                'id': update.effective_user.id,
                'full_name': context.user_data["full_name"],
                'phone': phone,
                'inviter_id': context.user_data["referrer_id"],
                'is_admin': False
            }

            if add_user(user_data):
                # علامت‌گذاری کد دعوت به عنوان استفاده شده
                referral = db.query(Referral).filter(
                    Referral.referral_code == context.user_data["referral_code"]
                ).first()

                if referral:
                    referral.used_by = user_data['id']
                    db.commit()

                await update.message.reply_text(
                    "✅ ثبت نام موفق!",
                    reply_markup=customer_kb
                )
            else:
                await update.message.reply_text("❌ خطا در ثبت اطلاعات!")

    except Exception as e:
        logger.error(f"خطا در ثبت نام: {str(e)}", exc_info=True)
        await update.message.reply


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
    try:
        phone = (
            update.message.contact.phone_number
            if update.message.contact
            else update.message.text.strip()
        )

        user_data = {
            'id': update.effective_user.id,
            'full_name': context.user_data["full_name"],
            'phone': phone,
            'is_admin': False
        }

        if add_user(user_data):
            await update.message.reply_text(
                "✅ ثبت نام موفق!",
                reply_markup=ReplyKeyboardMarkup([["منوی کاربری"]], resize_keyboard=True)
            )
        else:
            await update.message.reply_text("❌ خطا در ثبت اطلاعات!")

    except Exception as e:
        logger.error(f"خطا در ثبت نام: {str(e)}")
        await update.message.reply_text("❌ خطای سیستمی!")

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
    user = update.effective_user
    try:
        logger.info(f"درخواست لینک دعوت از کاربر {user.id}")

        # بررسی وجود کاربر در دیتابیس
        if not database.get_user(user.id):
            await update.message.reply_text("❌ لطفاً ابتدا ثبت نام کنید!")
            return

        # دریافت تعداد دعوت‌های باقی‌مانده
        remaining = database.get_remaining_invites(user.id)
        if remaining <= 0:
            await update.message.reply_text("❌ ظرفیت دعوت شما تکمیل شده است!")
            return

        # تولید کد رفرال جدید
        code, error = database.create_referral(user.id, is_admin=False)
        if error:
            await update.message.reply_text(f"❌ {error}")
            return

        # ساخت لینک دعوت با فرمت صحیح
        bot = await context.bot.get_me()
        referral_link = f"https://t.me/{bot.username}?start=ref_{code}"

        # ارسال پاسخ با فرمت HTML برای هایپرلینک
        await update.message.reply_text(
            f"🎉 <b>لینک دعوت شما:</b>\n"
            f"<a href='{referral_link}'>کلیک کنید برای دعوت</a>\n\n"
            f"🔢 تعداد دعوت باقی‌مانده: <b>{remaining}</b>\n"
            "⚠️ توجه: کاربر باید مستقیم روی لینک بالا کلیک کند!",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        logger.info(f"لینک دعوت برای کاربر {user.id} تولید شد: {code}")

    except Exception as e:
        logger.error(f"خطا در تولید لینک دعوت: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ خطای سیستمی! لطفاً مجدداً تلاش کنید.")


async def handle_gift_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        logger.debug(f"شروع پردازش درخواست هدیه برای کاربر {user.id}")

        # لاگ اطلاعات کاربر
        user_data = database.get_user(user.id)
        logger.debug(f"اطلاعات کاربر: {user_data}")

        # بررسی شرایط
        logger.debug("بررسی شرایط دریافت هدیه")
        if database.meets_gift_conditions(user.id):
            logger.debug("کاربر واجد شرایط است")

            # افزودن اعتبار
            logger.debug("در حال افزودن اعتبار...")
            if database.add_discount(user.id, 100):
                logger.debug("اعتبار با موفقیت افزوده شد")
                await update.message.reply_text("🎉 100 دلار اعتبار هدیه دریافت کردید!")
            else:
                logger.error("خطا در افزودن اعتبار")
                await update.message.reply_text("❌ خطا در اعطای هدیه!")

        else:
            logger.debug("کاربر واجد شرایط نیست")
            await update.message.reply_text("⚠️ شما شرایط دریافت هدیه را ندارید.")

    except Exception as e:
        logger.exception(f"خطای بحرانی: {str(e)}")
        await update.message.reply_text("❌ خطای سیستمی! لطفاً بعداً تلاش کنید.")


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