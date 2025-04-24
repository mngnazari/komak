import os


def find_selected_files(search_folders=['database', 'handlers', 'config', 'xxx']):
    """پیدا کردن تمام فایل‌های پایتون، YAML و ENV در پوشه‌های مشخص شده با آدرس کامل"""
    selected_files = []

    # بررسی فایل‌های پوشه جاری
    for file in os.listdir('.'):
        if file.endswith(('.py', '.yml', '.yaml', '.env')):
            selected_files.append(file)  # با پسوندهای مورد نظر

    # بررسی پوشه‌های دیگر
    for folder in search_folders:
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith(('.py', '.yml', '.yaml', '.env')):
                        full_path = os.path.join(root, file)
                        standardized_path = full_path.replace('/', '\\')
                        selected_files.append(standardized_path)

    return selected_files


def combine_files(file_paths, output_file='combined_modules.txt'):
    """ترکیب محتوای فایل‌ها در یک فایل متنی"""
    if os.path.exists(output_file):
        with open(output_file, 'w') as f:
            f.write('')

    with open(output_file, 'a', encoding='utf-8') as out_file:
        for path in file_paths:
            if not os.path.exists(path):
                print(f"خطا: فایل {path} یافت نشد!")
                continue

            try:
                with open(path, 'r', encoding='utf-8') as in_file:
                    content = in_file.read()

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

        if user_input == 'a':
            selected_files = all_files.copy()
            print("همه فایل‌ها انتخاب شدند.")
            continue

        if user_input == 's':
            if not selected_files:
                print("هیچ فایلی انتخاب نشده است!")
                continue
            return selected_files

        if user_input == 'u':
            if selected_files:
                removed = selected_files.pop()
                print(f"فایل {removed} از لیست انتخاب‌ها حذف شد.")
            else:
                print("لیست انتخاب‌ها خالی است!")
            continue

        if user_input == 'l':
            continue

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
    print("ترکیب‌کننده فایل‌های پایتون، YAML و ENV - نسخه پیشرفته")
    all_files = find_selected_files()

    print("\nفایل‌های موجود (پایتون، YAML و ENV):")
    for i, file_path in enumerate(all_files, 1):
        print(f"{i}: {file_path}")

    selected_files = get_user_selection(all_files)
    combine_files(selected_files)

    print("\nعملیات با موفقیت به پایان رسید!")
    print("نتایج در فایل 'combined_modules.txt' ذخیره شد.")