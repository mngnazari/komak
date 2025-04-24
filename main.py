import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers.user_handlers import start
from config import Config
from models import Base, engine

from telegram.ext import Application as TgApplication

from telegram.ext import (

    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

import database

from handlers.admin_handlers import admin_generate_referral, show_referral_tree
from handlers.file_handlers import (
    handle_files,
    handle_reply,  # اضافه شده
    handle_callback
)
from handlers.user_handlers import (
    FULL_NAME,
    PHONE,
    cancel_registration,
    get_full_name,
    get_phone,
    handle_active_orders,
    handle_archive,
    show_archive,
    start, generate_user_referral, handle_gift_request, show_direct_invites
)
import logging
from dotenv import load_dotenv
import os
from handlers.admin_handlers import admin_generate_referral
from models import Base, engine

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

load_dotenv()
ADMINS = [2138687434]  # آیدی ادمین اصلی را اینجا وارد کنید
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'charset': 'utf8mb4'
}
# در ابتدای main.py
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# غیرفعال کردن لاگ‌های کتابخانه‌های خارجی
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)





TOKEN = "7943645778:AAEXYzDKUc2D7mWaTcLrSkH4AjlJvVq7PaU"




def main():
    # ایجاد جداول اگر وجود ندارند
    Base.metadata.create_all(bind=engine)


    app = TgApplication.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            PHONE: [MessageHandler(filters.CONTACT | filters.TEXT & ~filters.COMMAND, get_phone)]
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_files))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_reply))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Regex("📂 آرشیو"), show_archive))
    app.add_handler(MessageHandler(filters.Regex("^(🕒 هفته اخیر|📅 ماه اخیر|📂 کل آرشیو)$"),handle_archive))
    app.add_handler(MessageHandler(
        filters.Regex(r"^🔄 درحال انجام(\(\d+\))?$"),  # قبول هر دو فرمت با و بدون عدد
        handle_active_orders
    ))
    # تغییر قسمت اضافه کردن هندلر
    app.add_handler(MessageHandler(filters.Regex("🔗 تولید لینک دعوت نامحدود"), admin_generate_referral))
    app.add_handler(CallbackQueryHandler(handle_callback))  # اضافه کردن هندلر
    # به لیست handlers اضافه کنید:

    # در بخش اضافه کردن هندلرها:
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^🎁 دریافت هدیه$"),  # مطمئن شوید متن دکمه دقیقاً همین باشد
            generate_user_referral
        )
    )
    app.add_handler(MessageHandler(filters.Regex("🌳 نمایش درخت دعوت"), show_referral_tree))
    app.add_handler(MessageHandler(filters.Regex("^👥 مدعوین من$"), show_direct_invites))
    # در تابع main یا جایی که هندلرها ثبت می‌شوند:
    app.add_handler(
        CommandHandler(
            "gen_ref",
            admin_generate_referral,
            filters=filters.User(user_id=ADMINS)  # استفاده از لیست ADMINS
        )
    )

    app.run_polling()


#
if __name__ == "__main__":
    main()