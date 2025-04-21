from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import database
import keyboards
from keyboards import get_qty_keyboard
import logging

logger = logging.getLogger(__name__)


async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not database.get_user(user.id):
        await update.message.reply_text("❌ لطفاً ابتدا ثبت نام کنید!")
        return

    doc = update.message.document
    file_data = (
        user.id,
        doc.file_name,
        doc.mime_type,
        doc.file_id,
        doc.file_unique_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        1,
        "فاقد توضیحات",
        "در حال انجام",
        ""
    )

    if not database.add_file(file_data):
        await update.message.reply_text("❌ خطا در ذخیره فایل!")
        return

    # کیبورد اصلاح شده
    keyboard = [
        [
            InlineKeyboardButton("تعداد 🧮", callback_data="edit_qty")
        ],
        [
            InlineKeyboardButton("انصراف ❌", callback_data="cancel_file")
        ]
    ]

    await update.message.reply_document(
        document=doc.file_id,
        caption=f"""⏰ زمان تحویل: تعیین نشده
🧮 تعداد: 1
📝 توضیحات: فاقد توضیحات
📌 برای افزودن توضیحات، روی پیام ریپلای کنید""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    message = query.message

    try:
        logger.debug(f"Callback data received: {data}")

        # دریافت file_id از پیام اصلی
        if not message.document:
            logger.error("No document found in the message!")
            return

        file_id = message.document.file_id
        logger.info(f"Processing file ID: {file_id}")

        # مدیریت انواع callback
        if data == "edit_qty":
            current_qty = database.get_file_quantity(file_id)
            await message.edit_reply_markup(
                reply_markup=keyboards.get_qty_keyboard(current_qty)
            )

        elif data in ("qty_up", "qty_down"):
            current_qty = int(message.reply_markup.inline_keyboard[0][1].text)

            if data == "qty_up":
                new_qty = current_qty + 1
            else:
                new_qty = max(1, current_qty - 1)

            # آپدیت کیبورد
            await message.edit_reply_markup(
                reply_markup=keyboards.get_qty_keyboard(new_qty)
            )

        elif data == "qty_confirm":
            final_qty = int(message.reply_markup.inline_keyboard[0][1].text)
            if database.update_file_quantity(file_id, final_qty):
                # آپدیت کپشن
                new_caption = message.caption.split('\n')
                new_caption[1] = f"🧮 تعداد: {final_qty}"
                await message.edit_caption(
                    caption="\n".join(new_caption),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("تعداد 🧮", callback_data="edit_qty")],
                        [InlineKeyboardButton("انصراف ❌", callback_data="cancel_file")]
                    ])
                )
            else:
                await query.answer("❌ خطا در بروزرسانی تعداد!")

        elif data == "qty_cancel":
            await message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("تعداد 🧮", callback_data="edit_qty")],
                    [InlineKeyboardButton("انصراف ❌", callback_data="cancel_file")]
                ])
            )

        elif data == "cancel_file":
            await message.delete()
            database.delete_file(file_id)  # نیاز به پیاده‌سازی تابع delete_file در دیتابیس

    except Exception as e:
        logger.error(f"Error in callback handler: {str(e)}", exc_info=True)
        await query.answer("⚠️ خطای سیستمی رخ داد!")


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پاسخ به پیام‌های ریپلای شده"""
    if not update.message.reply_to_message.document:
        return

    user = update.effective_user
    file_id = update.message.reply_to_message.document.file_id
    description = update.message.text.strip()

    # آپدیت توضیحات در دیتابیس
    if database.update_file_description(file_id, description):
        # آپدیت کپشن پیام
        new_caption = f"""
⏰ زمان تحویل: تعیین نشده
🧮 تعداد: {database.get_file_quantity(file_id)}
📝 توضیحات: {description}
        """.strip()

        keyboard = [
            [InlineKeyboardButton("تعداد 🧮", callback_data="edit_qty")],
            [InlineKeyboardButton("انصراف ❌", callback_data="cancel_file")]
        ]

        await update.message.reply_to_message.edit_caption(
            caption=new_caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text("✅ توضیحات با موفقیت ذخیره شد!")
    else:
        await update.message.reply_text("❌ خطا در ذخیره توضیحات!")
