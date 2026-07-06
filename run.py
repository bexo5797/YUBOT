# run.py
"""
نقطة التشغيل الرئيسية لبوت الملصقات
للتشغيل: python run.py
"""
import uvicorn
from main import app
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "bot.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=False,
        log_level="info"
    )
