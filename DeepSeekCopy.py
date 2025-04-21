2import os


def find_python_files(search_folders=['database', 'handlers', 'xxx']):
    """پیدا کردن تمام فایل‌های پایتون در پوشه‌های مشخص شده با آدرس کامل"""
    python_files = []

    # بررسی پوشه جاری2

    for file in os.listdir('.'):
        if file.endswith('.py'):
            python_files.append(file)  # با پسوند .py

    # بررسی پوشه‌های دیگر
    for folder in search_folders:
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith('.py'):
                        # ساخت مسیر کامل نسبت به پوشه جاری
                        full_path = os.path.join(root, file)
                        # تبدیل به فرمت استاندارد با بک‌اسلش
                        standardized_path = full_path.replace('/', '\\')
                        python_files.append(standardized_path)

    return python_files


def combine_files(file_paths, output_file='combined_modules.txt'):
    """ترکیب محتوای فایل‌های پایتون در یک فایل متنی"""
    # پاک کردن محتوای فایل خروجی اگر از قبل وجود دارد
    if os.path.exists(output_file):
        with open(output_file, 'w') as f:
            f.write('')

    with open(output_file, 'a', encoding='utf-8') as out_file:
        for path in file_paths:
            # اطمینان از وجود فایل
            if not os.path.exists(path):
                print(f"خطا: فایل {path} یافت نشد!")
                continue

            try:
                with open(path, 'r', encoding='utf-8') as in_file:
                    content = in_file.read()

                # نوشتن نام فایل به عنوان عنوان
                out_file.write(f"\n\n{'=' * 50}\n")
                out_file.write(f"# فایل: {path}\n")
                out_file.write(f"{'=' * 50}\n\n")
                out_file.write(content)

                print(f"فایل {path} با موفقیت اضافه شد.")

            except Exception as e:
                print(f"خطا در پردازش فایل {path}: {str(e)}")

    print(f"\nترکیب فایل‌ها با موفقیت در فایل {output_file} ذخیره شد.")


def get_user_selection(all_files):
    """دریافت انتخاب‌های کاربر به صورت یک‌به‌یک"""
    selected_files = []

    print("\nدستورالعمل:")
    print("- برای انتخاب فایل، عدد مربوط به آن را وارد کنید")
    print("- برای ترکیب همه فایل‌ها، کلید 'a' را بزنید")
    print("- برای پایان انتخاب‌ها و شروع ترکیب، کلید 's' را بزنید")
    print("- برای لغو انتخاب آخر، کلید 'u' را بزنید")
    print("- برای مشاهده مجدد لیست فایل‌ها، کلید 'l' را بزنید")

    while True:
        print("\nلیست فایل‌های موجود:")
        for i, file_path in enumerate(all_files, 1):
            print(f"{i}: {file_path}")

        print("\nفایل‌های انتخاب شده فعلی:")
        for f in selected_files:
            print(f"- {f}")

        print("\nعملیات مورد نظر را انتخاب کنید (عدد/a/s/u/l): ")
        user_input = input().lower()

        if user_input == 'a':  # انتخاب همه
            selected_files = all_files.copy()
            print("همه فایل‌ها انتخاب شدند.")
            continue

        if user_input == 's':  # شروع ترکیب
            if not selected_files:
                print("هیچ فایلی انتخاب نشده است!")
                continue
            return selected_files

        if user_input == 'u':  # لغو انتخاب آخر
            if selected_files:
                removed = selected_files.pop()
                print(f"فایل {removed} از لیست انتخاب‌ها حذف شد.")
            else:
                print("لیست انتخاب‌ها خالی است!")
            continue

        if user_input == 'l':  # نمایش مجدد لیست
            continue

        # انتخاب فایل بر اساس عدد
        try:
            index = int(user_input) - 1
            if 0 <= index < len(all_files):
                selected_file = all_files[index]
                if selected_file in selected_files:
                    print("این فایل قبلاً انتخاب شده است!")
                else:
                    selected_files.append(selected_file)
                    print(f"فایل {selected_file} به لیست انتخاب‌ها اضافه شد.")
            else:
                print("عدد وارد شده خارج از محدوده است!")
        except ValueError:
            print("ورودی نامعتبر! لطفاً عدد یا کلید عملیات را وارد کنید.")


if __name__ == "__main__":
    print("ترکیب‌کننده فایل‌های پایتون - نسخه پیشرفته")
    all_python_files = find_python_files()

    print("\nفایل‌های پایتون موجود:")
    for i, file_path in enumerate(all_python_files, 1):
        print(f"{i}: {file_path}")

    selected_files = get_user_selection(all_python_files)
    combine_files(selected_files)

    print("\nعملیات با موفقیت به پایان رسید!")
    print("می‌توانید نتایج را در فایل 'combined_modules.txt' مشاهده کنید.")