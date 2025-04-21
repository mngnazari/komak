# database_test.py
from database import (
    create_tables,
    add_user,
    create_referral,
    validate_referral,
    add_file,
    get_user,
    get_active_orders_count,
    delete_file,
    get_db_connection
)
from datetime import datetime
import mysql.connector


# ----------------------
# توابع کمکی برای تست
# ----------------------
def print_test_result(test_name, success):
    status = "✅ موفق" if success else "❌ شکست"
    print(f"{status} | تست: {test_name}")


# ----------------------
# تست‌های واحد
# ----------------------
def test_db_connection():
    """تست اتصال به دیتابیس"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        print_test_result("اتصال به دیتابیس", True)
    except Exception as e:
        print_test_result("اتصال به دیتابیس", False)
        print(f"خطا: {e}")


def test_create_tables():
    """تست ایجاد جداول"""
    try:
        create_tables()
        print_test_result("ایجاد جداول", True)
    except Exception as e:
        print_test_result("ایجاد جداول", False)
        print(f"خطا: {e}")


def test_user_flow():
    """تست کامل چرخه کاربر"""
    test_user_id = 999888777
    test_phone = "+989121234567"
    success = True

    try:
        # حذف کاربر تستی اگر وجود دارد
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM users WHERE id = {test_user_id}")
        conn.commit()

        # ۱. ثبت کاربر جدید
        user_data = (
            test_user_id,
            "کاربر تستی",
            test_phone,
            None
        )
        add_user(user_data)

        # ۲. بررسی وجود کاربر
        user = get_user(test_user_id)
        if not user:
            raise Exception("کاربر ایجاد نشد")

        # ۳. ایجاد کد دعوت
        code, error = create_referral(test_user_id)
        if not code:
            raise Exception("خطا در ایجاد کد دعوت")

        # ۴. اعتبارسنجی کد
        is_valid, referrer = validate_referral(code)
        if not is_valid:
            raise Exception("کد نامعتبر")

        # ۵. افزودن فایل
        file_data = (
            test_user_id,
            "test.stl",
            "application/stl",
            "FILE_TEST_123",
            "UNIQUE_TEST_123",
            datetime.now(),
            3,
            "توضیحات تست",
            "در حال انجام",
            ""
        )
        add_file(file_data)

        # ۶. بررسی تعداد سفارشات
        count = get_active_orders_count(test_user_id)
        if count != 1:
            raise Exception("مشکل در شمارش سفارشات")

        print_test_result("چرخه کامل کاربر", True)

    except Exception as e:
        print_test_result("چرخه کامل کاربر", False)
        print(f"خطا: {e}")
        success = False

    finally:
        # پاکسازی داده‌های تست
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM files WHERE user_id = {test_user_id}")
            cursor.execute(f"DELETE FROM users WHERE id = {test_user_id}")
            conn.commit()
        except:
            pass

        return success


# ----------------------
# اجرای تمام تست‌ها
# ----------------------
if __name__ == "__main__":
    print("\nشروع تست‌ها...\n")

    test_db_connection()
    test_create_tables()
    test_user_flow()

    print("\nپایان تست‌ها")