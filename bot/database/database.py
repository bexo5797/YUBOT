# bot/database/database.py
"""
إدارة قاعدة البيانات
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from sqlalchemy.engine import Engine
from ..config import settings
from ..utils.logger import logger

# إنشاء المحرك الأساسي
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# إنشاء مصنع الجلسات
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# إنشاء الفئة الأساسية للنماذج
Base = declarative_base()

async def get_db():
    """الحصول على جلسة قاعدة البيانات"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"خطأ في قاعدة البيانات: {e}")
            raise
        finally:
            await session.close()

async def init_db():
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    try:
        async with engine.begin() as conn:
            # استيراد النماذج للتأكد من تعريفها
            from . import models
            await conn.run_sync(Base.metadata.create_all)
        logger.info("تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
        raise

async def close_db():
    """إغلاق اتصال قاعدة البيانات"""
    await engine.dispose()
    logger.info("تم إغلاق اتصال قاعدة البيانات")

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """إعدادات SQLite الخاصة"""
    import sqlite3
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
