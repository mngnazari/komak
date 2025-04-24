# فایل جدید: utils.py
def generate_referral_link(bot_username: str, code: str) -> str:
    return f"https://t.me/{bot_username}?start=ref_{code}"