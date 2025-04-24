# فایل test.py
from sqlalchemy import text
from models import SessionLocal

def test_db_connection():
    try:
        with SessionLocal() as db:
            # اجرای کوئری تست با استفاده از text()
            db.execute(text("SELECT 1"))
            print("✅ اتصال موفقیت‌آمیز بود!")
            return True
    except Exception as e:
        print(f"❌ خطا در اتصال: {str(e)}")
        return False

if __name__ == "__main__":
    test_db_connection()