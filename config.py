import os


class Config:
    # تنظیمات دیتابیس
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", 3308)
    DB_USER = os.getenv("DB_USER", "testuser")
    DB_PASS = os.getenv("DB_PASS", "testpass")
    DB_NAME = os.getenv("DB_NAME", "print3d")

    # تنظیمات تلگرام
    TG_TOKEN = os.getenv("TG_TOKEN", "YOUR_BOT_TOKEN")

    # لیست ادمین‌ها (آیدی عددی)
    ADMINS = [2138687434]  # جایگزین کنید با آیدی واقعی ادمین

    # تنظیمات رفرال
    REFERRAL_CODE_LENGTH = 10
    ADMIN_CODE_PREFIX = "ADMIN_"