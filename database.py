from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from models import User, File, Referral, InvitedUser, Wallet, get_db, SessionLocal
from datetime import datetime, timedelta
import secrets
import string
import logging
from config import Config
from models import SessionLocal, User, Wallet

logger = logging.getLogger(__name__)

# تنظیمات پایه
ADMIN_ID = 2138687434

# ----------------------
# توابع اتصال به دیتابیس
# ----------------------
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        port=3308,          # پورتی که در Docker تنظیم کردید
        user='testuser',    # کاربر تعریف شده در docker-compose.yml
        password='testpass', # رمز عبور کاربر testuser
        database='print3d',
        connect_timeout = 30
    )

def is_admin(user_id: int) -> bool:
    try:
        with SessionLocal() as db:
            user = db.query(User).get(user_id)
            return user.is_admin if user else False
    except Exception as e:
        logger.error(f"خطا در بررسی ادمین: {str(e)}")
        return False

# ----------------------
# توابع کمکی
# ----------------------
def generate_referral_code(is_admin: bool = False) -> str:
    prefix = "ADMIN_" if is_admin else ""
    suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    return f"{prefix}{suffix}"

# ----------------------
# ایجاد جداول (بهینه‌سازی شده برای MySQL)
# ----------------------



# ----------------------
# توابع کاربران
# ----------------------
def add_user(user_data: dict) -> bool:
    try:
        with SessionLocal() as db:
            new_user = User(
                id=user_data['id'],
                full_name=user_data['full_name'],
                phone=user_data.get('phone', 'بدون شماره'),
                inviter_id=user_data.get('inviter_id'),
                is_admin=user_data.get('is_admin', False)
            )

            if new_user.is_admin:
                wallet = Wallet(user_id=new_user.id)
                db.add(wallet)

            db.add(new_user)
            db.commit()
            return True
    except Exception as e:
        logger.error(f"خطا در ثبت کاربر: {str(e)}")
        return False


# ----------------------
# توابع رفرال
# ----------------------
# ==============================
# ███ CREATING REFERRAL CODE ███
# ==============================
from mysql.connector import IntegrityError

def create_referral(db: Session, user_id: int, is_admin: bool = False) -> str:
    while True:
        code = generate_referral_code(is_admin)
        existing = db.query(Referral).filter(Referral.referral_code == code).first()
        if not existing:
            referral = Referral(
                referrer_id=user_id,
                referral_code=code,
                is_admin=is_admin,
                expires_at=datetime.now() + timedelta(days=365)
            )
            db.add(referral)
            db.commit()
            return code

# ----------------------
# توابع اعتبارسنجی رفرال
# ----------------------
def validate_referral(db, code: str):
    try:
        referral = db.query(Referral).filter(
            Referral.referral_code == code,
            Referral.used_by == None,
            Referral.expires_at > datetime.now()
        ).first()

        if not referral:
            return False, "کد دعوت نامعتبر یا منقضی شده است"
        return True, referral.referrer_id
    except SQLAlchemyError as e:
        logger.error(f"خطای اعتبارسنجی رفرال: {str(e)}")
        return False, "خطای سیستمی"


# ----------------------
# توابع مدیریت مدعوین
# ----------------------
def add_invited_user(referrer_id, user_data):
    """ذخیره اطلاعات کاربر دعوت شده با مدیریت تراکنش"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # تبدیل تاریخ به فرمت مناسب دیتابیس
        invited_at = datetime.now()
        full_data = (
            referrer_id,
            user_data[0],  # invited_user_id
            user_data[1],  # invited_full_name
            user_data[2],  # invited_phone
            invited_at
        )

        cursor.execute('''
            INSERT INTO invited_users 
            (referrer_id, invited_user_id, invited_full_name, invited_phone, invited_at)
            VALUES (%s, %s, %s, %s, %s)
        ''', full_data)

        conn.commit()
        logger.info(f"کاربر دعوت شده {user_data[0]} با موفقیت ثبت شد")
        return True

    except mysql.connector.IntegrityError as e:
        logger.error(f"خطای یکتایی در ثبت مدعو: {e}")
        return False
    except Exception as e:
        logger.error(f"خطا در ثبت مدعو: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def mark_referral_used(code, used_by):
    """علامت‌گذاری کد دعوت به عنوان استفاده شده"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE referrals 
            SET used_by = %s 
            WHERE referral_code = %s
        ''', (used_by, code))

        conn.commit()
        logger.info(f"کد دعوت {code} توسط کاربر {used_by} استفاده شد")
        return cursor.rowcount > 0

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در بروزرسانی رفرال: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_invited_users(referrer_id):
    """دریافت لیست مدعوین با فرمت منظم"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT 
                invited_full_name AS name,
                invited_phone AS phone,
                DATE_FORMAT(invited_at, '%%Y/%%m/%%d %%H:%%i') AS date
            FROM invited_users 
            WHERE referrer_id = %s
            ORDER BY invited_at DESC
        ''', (referrer_id,))

        return cursor.fetchall()

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در دریافت مدعوین: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def decrement_invites(user_id):
    """کاهش تعداد دعوت‌های باقی‌مانده کاربر"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users 
            SET remaining_invites = GREATEST(remaining_invites - 1, 0)
            WHERE id = %s
        ''', (user_id,))

        conn.commit()
        logger.debug(f"تعداد دعوت‌های کاربر {user_id} کاهش یافت")
        return cursor.rowcount > 0

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در کاهش دعوت‌ها: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ----------------------
# توابع کاربران (تکمیلی)
# ----------------------
def get_user(user_id):
    """دریافت اطلاعات کاربر با فرمت دیکشنری"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT 
                u.*,
                w.balance,
                w.discount
            FROM users u
            LEFT JOIN wallets w ON u.id = w.user_id
            WHERE u.id = %s
        ''', (user_id,))

        result = cursor.fetchone()
        if result:
            # تبدیل مقادیر عددی به نوع صحیح
            result['remaining_invites'] = int(result['remaining_invites'])
            result['balance'] = float(result['balance'])
            result['discount'] = float(result['discount'])

        return result

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در دریافت کاربر: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ----------------------
# توابع مدیریت فایل‌ها
# ----------------------
def get_active_orders(user_id):
    """دریافت سفارشات فعال کاربر با فرمت دیکشنری"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                id,
                file_name,
                quantity,
                status,
                created_at
            FROM files 
            WHERE user_id = %s 
                AND status = 'در حال انجام'
            ORDER BY created_at DESC
        """, (user_id,))

        orders = []
        for order in cursor.fetchall():
            # تبدیل تاریخ به فرمت قابل خواندن
            order['created_at'] = order['created_at'].strftime("%Y/%m/%d %H:%M")
            orders.append(order)

        return orders

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در دریافت سفارشات: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_active_orders_count(user_id):
    """دریافت تعداد سفارشات فعال با بهینه‌سازی کوئری"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(id) 
            FROM files 
            WHERE user_id = %s 
                AND status = 'در حال انجام'
        """, (user_id,))

        return cursor.fetchone()[0] or 0

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در شمارش سفارشات: {e}")
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def add_file(file_data):
    """ذخیره امن اطلاعات فایل با مدیریت تراکنش"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # اعتبارسنجی داده‌های ورودی
        required_fields = [
            'user_id', 'file_name', 'mime_type',
            'file_id', 'file_unique_id', 'created_at'
        ]
        if len(file_data) < 6:
            raise ValueError("داده‌های فایل ناقص است")

        # درج فایل جدید
        cursor.execute('''
            INSERT INTO files (
                user_id, file_name, mime_type,
                file_id, file_unique_id, created_at,
                quantity, description, status, notes
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s,
                COALESCE(%s, 1),  # مقدار پیشفرض برای تعداد
                COALESCE(%s, 'فاقد توضیحات'),
                COALESCE(%s, 'در حال انجام'),
                COALESCE(%s, '')
            )
        ''', file_data)

        conn.commit()
        logger.info(f"فایل جدید با ID {cursor.lastrowid} ثبت شد")
        return True

    except mysql.connector.IntegrityError as e:
        logger.error(f"خطای یکتایی فایل: {e}")
        return False
    except Exception as e:
        logger.error(f"خطا در ثبت فایل: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_files_by_user(user_id, days=None):
    """دریافت فایل‌های کاربر با فیلتر زمانی"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                id,
                file_name,
                quantity,
                status,
                created_at
            FROM files 
            WHERE user_id = %s
        """
        params = [user_id]

        if days and days > 0:
            query += " AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"
            params.append(days)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)

        files = []
        for file in cursor.fetchall():
            file['created_at'] = file['created_at'].strftime("%Y/%m/%d")
            files.append(file)

        return files

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در دریافت فایل‌ها: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_file_description(file_id, description):
    """به روزرسانی توضیحات فایل با اعتبارسنجی"""
    conn = None
    cursor = None
    try:
        if not description or len(description) > 500:
            raise ValueError("توضیحات نامعتبر")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE files 
            SET description = %s 
            WHERE file_id = %s
        """, (description, file_id))

        conn.commit()
        logger.info(f"توضیحات فایل {file_id} به‌روزرسانی شد")
        return cursor.rowcount > 0

    except ValueError as e:
        logger.warning(f"خطای اعتبارسنجی: {e}")
        return False
    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در بروزرسانی: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_file_quantity(file_id):
    """دریافت تعداد فایل با مدیریت خطا"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(quantity, 1) 
            FROM files 
            WHERE file_id = %s
        """, (file_id,))

        result = cursor.fetchone()
        return result[0] if result else 1

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در دریافت تعداد: {e}")
        return 1
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_file_quantity(file_id, new_qty):
    """به روزرسانی تعداد با اعتبارسنجی مقدار ورودی"""
    conn = None
    cursor = None
    try:
        if not isinstance(new_qty, int) or new_qty < 1:
            raise ValueError("تعداد نامعتبر")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE files 
            SET quantity = GREATEST(%s, 1) 
            WHERE file_id = %s
        """, (new_qty, file_id))

        conn.commit()
        logger.info(f"تعداد فایل {file_id} به {new_qty} به‌روزرسانی شد")
        return cursor.rowcount > 0

    except ValueError as e:
        logger.warning(f"خطای اعتبارسنجی تعداد: {e}")
        return False
    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در بروزرسانی تعداد: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def delete_file(file_id):
    """حذف امن فایل با بررسی وجود رکورد"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # بررسی وجود فایل قبل از حذف
        cursor.execute("SELECT id FROM files WHERE file_id = %s", (file_id,))
        if not cursor.fetchone():
            logger.warning(f"فایل با شناسه {file_id} یافت نشد")
            return False

        cursor.execute("DELETE FROM files WHERE file_id = %s", (file_id,))
        conn.commit()
        logger.info(f"فایل {file_id} با موفقیت حذف شد")
        return True

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در حذف فایل: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ----------------------
# توابع مدیریت دعوت‌ها و هدایا
# ----------------------
def get_remaining_invites(user_id):
    """دریافت تعداد دعوت‌های باقی‌مانده کاربر"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(remaining_invites, 0)
            FROM users 
            WHERE id = %s
        """, (user_id,))

        result = cursor.fetchone()
        return result[0] if result else 0

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس در دریافت دعوت‌ها: {e}")
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def add_discount(user_id, amount):
    """افزودن تخفیف به کیف پول کاربر با اعتبارسنجی"""
    conn = None
    cursor = None
    try:
        # اعتبارسنجی مقدار تخفیف
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("مقدار تخفیف نامعتبر")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE wallets 
            SET discount = discount + %s 
            WHERE user_id = %s
        """, (amount, user_id))

        conn.commit()
        logger.info(f"تخفیف {amount} به کاربر {user_id} افزوده شد")
        return cursor.rowcount > 0

    except ValueError as e:
        logger.warning(f"خطای اعتبارسنجی: {e}")
        return False
    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def meets_gift_conditions(user_id):
    """بررسی شرایط دریافت هدیه"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                COUNT(*) AS total_completed,
                SUM(quantity) AS total_quantity
            FROM files 
            WHERE 
                user_id = %s 
                AND status = 'تکمیل شده'
                AND created_at >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
        """, (user_id,))

        result = cursor.fetchone()
        return result['total_completed'] >= 3 and result['total_quantity'] >= 10

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_completed_orders(user_id):
    """دریافت سفارشات تکمیل شده با فرمت‌بندی"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                id,
                file_name,
                quantity,
                DATE_FORMAT(created_at, '%%Y/%%m/%%d %%H:%%i') AS created_at,
                description
            FROM files 
            WHERE 
                user_id = %s 
                AND status = 'تکمیل شده'
            ORDER BY created_at DESC
        """, (user_id,))

        return cursor.fetchall()

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ----------------------
# توابع درخت دعوت
# ----------------------
def get_referral_tree(user_id):
    """دریافت ساختار درختی دعوت‌ها"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            WITH RECURSIVE referral_tree AS (
                SELECT 
                    id,
                    full_name,
                    phone,
                    inviter_id,
                    0 AS level
                FROM users
                WHERE id = %s

                UNION ALL

                SELECT 
                    u.id,
                    u.full_name,
                    u.phone,
                    u.inviter_id,
                    rt.level + 1
                FROM users u
                INNER JOIN referral_tree rt ON u.inviter_id = rt.id
            )
            SELECT * FROM referral_tree
            ORDER BY level ASC
        """, (user_id,))

        return cursor.fetchall()

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def format_referral_tree(tree_data):
    """قالب‌بندی درخت دعوت به صورت متن سلسله مراتبی"""
    try:
        tree = {}
        for item in tree_data:
            tree.setdefault(item['inviter_id'], []).append(item)

        def build_branch(parent_id, level=0):
            branch = []
            for child in tree.get(parent_id, []):
                prefix = "│   " * (level - 1) + "├── " if level > 0 else ""
                branch.append(f"{prefix}👤 {child['full_name']} ({child['phone']})")
                branch.extend(build_branch(child['id'], level + 1))
            return branch

        return "\n".join(build_branch(None))

    except Exception as e:
        logger.error(f"خطا در فرمت‌بندی: {e}")
        return "خطا در نمایش ساختار"


# ----------------------
# توابع مدیریت مدعوین
# ----------------------
def get_direct_invites(user_id):
    """دریافت لیست مدعوین مستقیم با جزئیات"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                invited_full_name AS name,
                invited_phone AS phone,
                DATE_FORMAT(invited_at, '%%Y/%%m/%%d') AS date
            FROM invited_users 
            WHERE referrer_id = %s
            ORDER BY invited_at DESC
        """, (user_id,))

        return cursor.fetchall()

    except mysql.connector.Error as e:
        logger.error(f"خطای دیتابیس: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
if __name__ == "__main__":
    create_tables()  # این خط باید وجود داشته باشد