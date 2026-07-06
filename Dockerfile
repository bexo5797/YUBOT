FROM python:3.10-slim

WORKDIR /app

# تثبيت الاعتماديات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الملفات
COPY . .

# إنشاء مجلد للملفات
RUN mkdir -p manga_files

# تشغيل البوت
CMD ["python", "bot.py"]
