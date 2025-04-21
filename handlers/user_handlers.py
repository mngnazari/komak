from telegram import Update, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
import database
import keyboards
from keyboards import customer_kb, admin_kb, wallet_kb, archive_reply_kb
from jdatetime import datetime as jdatetime

import logging
import sqlite3
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
    args = context.args
    # ثبت خودکار ادمین اگر وجود ندارد
    if user.id == ADMIN_ID:
        admin_data = {
            'id': user.id,
            'full_name': "ادمین سیستم",
            'phone': "بدون شماره",
            'is_admin': True
        }
        if not database.get_user(user.id):
            database.add_user(admin_data)
        await update.message.reply_text("👑 پنل مدیریتی فعال شد!", reply_markup=keyboards.admin_kb)
        return ConversationHandler.END


    # اگر کاربر ادمین است و در جدول وجود ندارد، ثبت شود
    if user.id == database.ADMIN_ID and not database.get_user(user.id):
        user_data = (
            user.id,
            "ادمین",  # نام کامل ادمین
            "بدون شماره",  # شماره تماس (اختیاری)
            None,  # inviter_id برای ادمین None است
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        database.add_user(user_data)

    # اگر ادمین باشد
    if user.id == ADMIN_ID:
        await update.message.reply_text("👑 پنل مدیریتی فعال شد!", reply_markup=admin_kb)
        return ConversationHandler.END

    # بررسی ثبت‌نام قبلی
    if database.get_user(user.id):
        await update.message.reply_text("✅ قبلاً ثبت نام کرده‌اید!")
        return ConversationHandler.END

    # استخراج کد رفرال
    referral_code = None
    if args:
        for arg in args:
            if arg.startswith("ref_"):
                referral_code = arg[4:]
                break

    if not referral_code:
        await update.message.reply_text("🔒 دسترسی فقط از طریق لینک دعوت ممکن است!")
        return ConversationHandler.END

    context.user_data["referral_code"] = referral_code
    await update.message.reply_text("👤 لطفاً نام کامل خود را وارد کنید:")
    return FULL_NAME



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
        # دریافت شماره تماس
        if update.message.contact:
            phone = update.message.contact.phone_number
        else:
            phone = update.message.text.strip()
            if not phone.startswith('+'):
                phone = f"+98{phone[-10:]}"  # فرمت ایران

        # اعتبارسنجی نهایی کد رفرال
        referral_code = context.user_data.get("referral_code")
        is_valid, referrer_id = database.validate_referral(referral_code)

        if not is_valid:
            await update.message.reply_text(f"❌ {referrer_id}")
            context.user_data.clear()
            return ConversationHandler.END

        # آماده‌سازی داده‌های کاربر
        user_data = (
            user.id,
            context.user_data["full_name"],
            phone,
            referrer_id,  # inviter_id از کد رفرال
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # ذخیره کاربر جدید
        if database.add_user(user_data):
            # ثبت مدعو در لیست دعوت‌کننده
            invited_user_data = (
                user.id,
                context.user_data["full_name"],
                phone,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            # افزودن به جدول مدعوین
            success = database.add_invited_user(
                referrer_id=referrer_id,
                user_data=invited_user_data
            )

            if not success:
                logging.error(f"خطا در ثبت مدعو برای کاربر {user.id}")

            # کاهش تعداد دعوت‌های باقی‌مانده (اگر کاربر عادی باشد)
            if referrer_id != database.ADMIN_ID:
                database.decrement_invites(referrer_id)
                database.add_discount(referrer_id, 50)

            # علامت‌گذاری کد رفرال به عنوان استفاده شده
            database.mark_referral_used(referral_code, user.id)

            await update.message.reply_text(
                "✅ ثبت نام موفق! لطفا از منوی زیر استفاده کنید:",
                reply_markup=keyboards.customer_kb
            )
        else:
            await update.message.reply_text("❌ خطا در ثبت اطلاعات کاربر!")

    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ این شماره قبلاً ثبت شده است!")
    except Exception as e:
        logging.exception(f"🔥 خطای بحرانی: {str(e)}")
        await update.message.reply_text("❌ خطای سیستمی! لطفاً مجدد تلاش کنید.")
    finally:
        context.user_data.clear()
        return ConversationHandler.END


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

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرایند ثبت نام"""
    await update.message.reply_text(
        "❌ ثبت نام لغو شد.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


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