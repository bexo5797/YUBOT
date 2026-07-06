from pymongo import MongoClient
from config import Config
import datetime

class Database:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI)
        self.db = self.client[Config.DATABASE_NAME]
        self.manga_collection = self.db["manga"]
        self.chapters_collection = self.db["chapters"]
        self.users_collection = self.db["users"]
        
    # إدارة المانجا
    def add_manga(self, manga_id, name, author, description, cover):
        return self.manga_collection.insert_one({
            "manga_id": manga_id,
            "name": name,
            "author": author,
            "description": description,
            "cover": cover,
            "created_at": datetime.datetime.now()
        })
    
    def get_manga_list(self):
        return list(self.manga_collection.find({}, {"_id": 0}))
    
    def get_manga(self, manga_id):
        return self.manga_collection.find_one({"manga_id": manga_id}, {"_id": 0})
    
    # إدارة الفصول
    def add_chapter(self, manga_id, chapter_number, files, title=None):
        return self.chapters_collection.insert_one({
            "manga_id": manga_id,
            "chapter": chapter_number,
            "title": title or f"Chapter {chapter_number}",
            "files": files,  # قائمة بأسماء الملفات
            "created_at": datetime.datetime.now()
        })
    
    def get_chapters(self, manga_id):
        return list(self.chapters_collection.find(
            {"manga_id": manga_id}, 
            {"_id": 0}
        ).sort("chapter", 1))
    
    def get_chapter(self, manga_id, chapter_number):
        return self.chapters_collection.find_one(
            {"manga_id": manga_id, "chapter": chapter_number},
            {"_id": 0}
        )
    
    # إدارة المستخدمين
    def add_user(self, user_id, username=None):
        if not self.users_collection.find_one({"user_id": user_id}):
            return self.users_collection.insert_one({
                "user_id": user_id,
                "username": username,
                "joined_at": datetime.datetime.now()
            })
        return None
    
    def get_user_count(self):
        return self.users_collection.count_documents({})
    
    # حذف المانجا
    def delete_manga(self, manga_id):
        self.manga_collection.delete_one({"manga_id": manga_id})
        self.chapters_collection.delete_many({"manga_id": manga_id})
