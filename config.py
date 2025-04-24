import os


class Config:
    # تنظیمات دیتابیس
    DB_HOST = '127.0.0.1'
    DB_PORT =3308  # تبدیل به عدد
    DB_USER ='testuser'
    DB_PASS = 'testpass'
    DB_NAME ='print3d'

    # تنظیمات تلگرام
    TG_TOKEN = os.getenv("TG_TOKEN", "YOUR_BOT_TOKEN")

    # لیست ادمین‌ها (آیدی عددی)
    ADMINS = [2138687434]  # جایگزین کنید با آیدی واقعی ادمین

    # تنظیمات رفرال
    REFERRAL_CODE_LENGTH = 10
    ADMIN_CODE_PREFIX = "ADMIN_"