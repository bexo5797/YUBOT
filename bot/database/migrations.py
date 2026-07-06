# bot/database/migrations.py
"""
إدارة ترحيل قاعدة البيانات
"""
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from .database import engine, Base
from ..utils.logger import logger
import json
from datetime import datetime

class Migration:
    """نظام إدارة ترحيل قاعدة البيانات"""
    
    def __init__(self):
        self.migrations: List[Dict[str, Any]] = [
            {
                "version": "1.0.0",
                "description": "التهيئة الأولية لقاعدة البيانات",
                "sql": """
                    -- إنشاء جداول البداية
                """
            },
            {
                "version": "1.1.0",
                "description": "إضافة جدول الإعدادات",
                "sql": """
                    -- تحديث بنية قاعدة البيانات
                """
            }
        ]
    
    async def run_migrations(self):
        """تشغيل جميع الترحيلات"""
        try:
            async with engine.begin() as conn:
                # إنشاء جدول الترحيلات إذا لم يكن موجوداً
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version VARCHAR(32) NOT NULL UNIQUE,
                        description TEXT,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # الحصول على الترحيلات المطبقة
                result = await conn.execute(text(
                    "SELECT version FROM migrations ORDER BY version"
                ))
                applied_versions = {row[0] for row in result}
                
                # تطبيق الترحيلات الجديدة
                for migration in self.migrations:
                    if migration["version"] not in applied_versions:
                        logger.info(f"تطبيق الترحيل: {migration['version']} - {migration['description']}")
                        
                        # تنفيذ SQL
                        if migration["sql"].strip():
                            await conn.execute(text(migration["sql"]))
                        
                        # تسجيل الترحيل
                        await conn.execute(
                            text("INSERT INTO migrations (version, description) VALUES (:version, :description)"),
                            {"version": migration["version"], "description": migration["description"]}
                        )
                        
                        logger.info(f"تم تطبيق الترحيل: {migration['version']}")
                
                # إنشاء جميع الجداول
                await conn.run_sync(Base.metadata.create_all)
                
            logger.info("تم الانتهاء من جميع الترحيلات")
            
        except Exception as e:
            logger.error(f"خطأ في تطبيق الترحيلات: {e}")
            raise
    
    async def get_migration_status(self) -> List[Dict]:
        """الحصول على حالة الترحيلات"""
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text(
                    "SELECT version, description, applied_at FROM migrations ORDER BY version"
                ))
                return [
                    {
                        "version": row[0],
                        "description": row[1],
                        "applied_at": row[2]
                    }
                    for row in result
                ]
        except Exception:
            return []

# مثيل عالمي
migration_manager = Migration()
