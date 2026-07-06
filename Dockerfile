# استخدام Python 3.11
FROM python:3.11-slim

# تثبيت FFmpeg والاعتماديات
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملفات المتطلبات أولاً (للتخزين المؤقت)
COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY . .

# إنشاء المجلدات المطلوبة
RUN mkdir -p stickers videos

# تعيين متغيرات البيئة
ENV PYTHONUNBUFFERED=1

# فتح المنفذ (افتراضي)
EXPOSE 8443

# تشغيل البوت
CMD ["python", "bot.py"]
