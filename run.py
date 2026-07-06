# run.py
"""
نقطة التشغيل الرئيسية لبوت الملصقات
للتشغيل: python run.py
"""
import uvicorn
from bot.main import app
from bot.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "bot.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=False,
        log_level="info"
    )
