# bot/main.py
"""
الملف الرئيسي للتطبيق - إعداد البوت و FastAPI
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from telegram import Update, Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import uvicorn
from pathlib import Path
import sys
import os

# إضافة المسار الرئيسي للمشروع
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import settings
from .utils.logger import logger, setup_logger
from .database.database import init_db, close_db
from .database.migrations import migration_manager

# استيراد المعالجات
from .handlers.start import start_handler, language_handler
from .handlers.photo import photo_handler, emoji_handler
from .handlers.video import video_handler, animation_handler
from .handlers.pack import (
    create_pack_handler,
    my_packs_handler,
    delete_pack_handler,
    share_pack_handler
)
from .handlers.callback import callback_query_handler
from .handlers.settings import settings_handler, statistics_handler
from .handlers.admin import (
    admin_handler,
    admin_stats_handler,
    admin_users_handler,
    admin_broadcast_handler,
    admin_packs_handler
)
from .handlers.errors import global_error_handler

# إنشاء تطبيق FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """دورة حياة التطبيق"""
    # بدء التشغيل
    logger.info("=" * 50)
    logger.info("بدء تشغيل بوت الملصقات...")
    logger.info(f"الوضع: {'Webhook' if settings.WEBHOOK_URL else 'Polling'}")
    logger.info(f"المنفذ: {settings.PORT}")
    logger.info("=" * 50)
    
    # تهيئة قاعدة البيانات
    await init_db()
    
    # تشغيل الترحيلات
    await migration_manager.run_migrations()
    
    # إنشاء مجلدات مؤقتة
    temp_dir = Path("data/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # تهيئة التطبيق وبدء البوت
    await initialize_bot()
    
    yield
    
    # إيقاف التشغيل
    logger.info("جاري إيقاف البوت...")
    
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()
    
    await close_db()
    logger.info("تم إيقاف البوت")

# إنشاء تطبيق FastAPI
app = FastAPI(
    title="Telegram Sticker Bot API",
    description="Professional Telegram Sticker Bot with FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

# متغير عام لتطبيق البوت
bot_app: Application = None
bot_instance: Bot = None

async def initialize_bot():
    """تهيئة وإعداد البوت"""
    global bot_app, bot_instance
    
    try:
        # إنشاء البوت
        bot_instance = Bot(token=settings.BOT_TOKEN)
        
        # بناء التطبيق
        builder = ApplicationBuilder()
        builder.token(settings.BOT_TOKEN)
        builder.bot(bot_instance)
        
        # إعدادات إضافية
        builder.concurrent_updates(True)
        builder.arbitrary_callback_data(True)
        
        # بناء التطبيق
        bot_app = builder.build()
        
        # تسجيل المعالجات
        register_handlers()
        
        # تسجيل معالج الأخطاء
        bot_app.add_error_handler(global_error_handler)
        
        # بدء التطبيق
        await bot_app.initialize()
        
        if settings.WEBHOOK_URL:
            # وضع Webhook
            webhook_url = f"{settings.WEBHOOK_URL}/webhook"
            await bot_app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=Update.ALL_TYPES
            )
            logger.info(f"تم تعيين Webhook: {webhook_url}")
        else:
            # وضع Polling
            await bot_app.start()
            asyncio.create_task(bot_app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            ))
            logger.info("بدء وضع Polling")
        
        # الحصول على معلومات البوت
        bot_info = await bot_instance.get_me()
        logger.info(f"البوت جاهز: @{bot_info.username}")
        
    except Exception as e:
        logger.error(f"خطأ في تهيئة البوت: {e}")
        raise

def register_handlers():
    """تسجيل جميع معالجات الأوامر والرسائل"""
    
    # أوامر أساسية
    bot_app.add_handler(start_handler)
    bot_app.add_handler(language_handler)
    
    # أوامر الحزم
    bot_app.add_handler(create_pack_handler)
    bot_app.add_handler(my_packs_handler)
    bot_app.add_handler(delete_pack_handler)
    bot_app.add_handler(share_pack_handler)
    
    # أوامر الإعدادات
    bot_app.add_handler(settings_handler)
    bot_app.add_handler(statistics_handler)
    
    # أوامر المشرف
    bot_app.add_handler(admin_handler)
    bot_app.add_handler(admin_stats_handler)
    bot_app.add_handler(admin_users_handler)
    bot_app.add_handler(admin_broadcast_handler)
    bot_app.add_handler(admin_packs_handler)
    
    # معالجات الملفات
    bot_app.add_handler(photo_handler)
    bot_app.add_handler(video_handler)
    bot_app.add_handler(animation_handler)
    
    # معالج الأزرار
    bot_app.add_handler(callback_query_handler)
    
    # معالج الإيموجي (يجب أن يكون بعد معالجات الأوامر)
    bot_app.add_handler(emoji_handler)
    
    logger.info("تم تسجيل جميع المعالجات")

# نقاط نهاية API

@app.get("/")
async def root():
    """نقطة النهاية الرئيسية"""
    return {
        "status": "online",
        "bot": settings.BOT_USERNAME,
        "version": "1.0.0",
        "mode": "webhook" if settings.WEBHOOK_URL else "polling"
    }

@app.get("/health")
async def health_check():
    """نقطة فحص الصحة"""
    try:
        # التحقق من حالة البوت
        if bot_instance:
            bot_info = await bot_instance.get_me()
            return {
                "status": "healthy",
                "bot": bot_info.username,
                "database": "connected"
            }
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": "Bot not initialized"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.post("/webhook")
async def webhook(request: Request):
    """نقطة نهاية Webhook"""
    if not settings.WEBHOOK_URL:
        return JSONResponse(
            status_code=404,
            content={"error": "Webhook mode not enabled"}
        )
    
    try:
        # قراءة بيانات التحديث
        data = await request.json()
        update = Update.de_json(data, bot_instance)
        
        # معالجة التحديث
        if bot_app:
            await bot_app.process_update(update)
            return {"status": "ok"}
        else:
            return JSONResponse(
                status_code=503,
                content={"error": "Bot not ready"}
            )
            
    except Exception as e:
        logger.error(f"خطأ في معالجة Webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/stats")
async def get_stats():
    """نقطة نهاية الإحصائيات"""
    try:
        from .database.crud import UserCRUD, PackCRUD
        from .database.database import get_db
        
        async for db in get_db():
            user_crud = UserCRUD(db)
            pack_crud = PackCRUD(db)
            
            total_users = await user_crud.get_users_count()
            total_packs = await pack_crud.get_total_packs_count()
            
            return {
                "users": total_users,
                "packs": total_packs,
                "uptime": "active",
                "mode": "webhook" if settings.WEBHOOK_URL else "polling"
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/setup-webhook")
async def setup_webhook(url: str = None):
    """إعداد Webhook يدوياً"""
    try:
        webhook_url = url or settings.WEBHOOK_URL
        
        if not webhook_url:
            return {"error": "Webhook URL is required"}
        
        if bot_instance:
            full_url = f"{webhook_url}/webhook"
            await bot_instance.set_webhook(url=full_url)
            
            webhook_info = await bot_instance.get_webhook_info()
            
            return {
                "status": "success",
                "webhook_url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count
            }
        
        return {"error": "Bot not initialized"}
        
    except Exception as e:
        return {"error": str(e)}

@app.delete("/webhook")
async def remove_webhook():
    """حذف Webhook"""
    try:
        if bot_instance:
            await bot_instance.delete_webhook()
            return {"status": "webhook removed"}
        return {"error": "Bot not initialized"}
    except Exception as e:
        return {"error": str(e)}

# تشغيل التطبيق مباشرة (للتطوير)
if __name__ == "__main__":
    uvicorn.run(
        "bot.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )
