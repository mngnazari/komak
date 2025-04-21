from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

import database

# کیبورد کاربران
# کیبورد پایه بدون نمایش تعداد
# کیبورد کاربران
# فایل keyboards.py
customer_kb = ReplyKeyboardMarkup(
    [
        ["📂 آرشیو", "🔄 درحال انجام"],
        ["💳 کیف پول", "📞 پشتیبانی"],
        ["📜 قوانین", "🧾 فاکتور"],
        ["🎁 دریافت هدیه", "👥 مدعوین من"] # اضافه شدن دکمه جدید
    ],
    resize_keyboard=True,
    is_persistent=True
)

archive_reply_kb = ReplyKeyboardMarkup(
    [
        ["🕒 هفته اخیر", "📅 ماه اخیر"],
        ["📂 کل آرشیو", "🔙 برگشت"]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# کیبورد ادمین باید دقیقاً همین متن را داشته باشد
admin_kb = ReplyKeyboardMarkup(
    [
        ["🔗 تولید لینک دعوت نامحدود"],
        ["👥 لیست مشتریان", "📊 آمار سیستم"],
        ["🌳 نمایش درخت دعوت"]  # دکمه جدید
    ],
    resize_keyboard=True
)

def get_qty_keyboard(current_qty=1):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("-", callback_data="qty_down"),
            InlineKeyboardButton(str(current_qty), callback_data="noop"),
            InlineKeyboardButton("+", callback_data="qty_up")
        ],
        [
            InlineKeyboardButton("تأیید ✅", callback_data="qty_confirm"),
            InlineKeyboardButton("لغو ↩️", callback_data="qty_cancel")
        ]
    ])

# کیبورد کیف پول
wallet_kb = ReplyKeyboardMarkup(
    [
        ["💵 موجودی کیف", "🎫 اعتبار تخفیف"],
        ["🔙 برگشت"]
    ],
    resize_keyboard=True
)
#
# فایل: database.py
# ...

def get_customer_kb(user_id):
    """تهیه کیبورد مشتری با نمایش تعداد سفارشات فعال"""
    active_orders = database.get_active_orders_count(user_id)
    return ReplyKeyboardMarkup(
        keyboard=[
            ["📂 آرشیو", f"🔄 درحال انجام ({active_orders})"],
            ["💳 کیف پول", "📞 پشتیبانی"],
            ["📜 قوانین", "🧾 فاکتور"],
            ["🎁 دریافت هدیه", "👥 مدعوین من"]  # اضافه شدن دکمه جدید
        ],
        resize_keyboard=True,
        is_persistent=True
    )