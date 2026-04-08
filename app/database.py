# app/database.py
from bson import ObjectId
import os
import random
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

_client = None
_database = None


async def get_db():
    """Получить экземпляр базы данных (гарантирует инициализацию)"""
    global _client, _database
    
    if _database is None:
        if _client is None:
            _client = AsyncIOMotorClient(MONGO_URI)
        _database = _client[MONGO_DB_NAME]
        # Проверяем подключение
        await _client.admin.command('ping')
        print(f"✅ Подключено к MongoDB: {MONGO_DB_NAME}")
        
        # Создаем индексы для быстрого поиска
        try:
            await _database.users.create_index("user_id", unique=True)
            await _database.test_sessions.create_index("user_id")
            await _database.results.create_index("user_id")
            print("✅ Индексы созданы")
        except Exception as e:
            print(f"⚠️ Ошибка при создании индексов: {e}")
    
    return _database


async def init_db():
    """Инициализация (алиас для get_db для совместимости)"""
    return await get_db()


async def close_db():
    """Закрытие подключения"""
    global _client, _database
    if _client:
        _client.close()
        _database = None
        _client = None
        print("🔌 Соединение с MongoDB закрыто")


async def load_tests_from_dict(tests_database):
    """Загрузка тестов из словаря в MongoDB (только при первом запуске)"""
    db = await get_db()
    topics_collection = db["topics"]
    
    # Проверяем, есть ли уже данные
    if await topics_collection.count_documents({}) > 0:
        print("📚 Тесты уже загружены, пропускаем...")
        return
    
    print("🔄 Загрузка тестов в MongoDB...")
    
    for subject_name, topics in tests_database.items():
        for topic_name, questions in topics.items():
            topic_doc = {
                "subject": subject_name,
                "topic": topic_name,
                "questions": []
            }
            
            for q in questions:
                question_doc = {
                    "text": q["question"],
                    "type": q.get("type", "test"),
                    "options": q.get("options"),
                    "correct_option": q.get("correct"),
                    "correct_answer": q.get("correct_answer"),
                    "hint": q.get("hint"),
                    "keywords": q.get("keywords")
                }
                topic_doc["questions"].append(question_doc)
            
            await topics_collection.insert_one(topic_doc)
            print(f"  ✅ {subject_name} -> {topic_name} ({len(questions)} вопросов)")
    
    print("✅ Все тесты загружены!")


async def get_all_subjects():
    """Получить список всех предметов"""
    db = await get_db()
    topics_collection = db["topics"]
    subjects = await topics_collection.distinct("subject")
    return sorted(subjects)


async def get_topics_by_subject(subject: str):
    """Получить список тем по предмету"""
    db = await get_db()
    topics_collection = db["topics"]
    cursor = topics_collection.find({"subject": subject}, {"topic": 1, "_id": 0})
    topics = await cursor.to_list(length=None)
    return [t["topic"] for t in topics]


async def get_questions_by_topic(subject: str, topic: str):
    """Получить все вопросы по теме"""
    db = await get_db()
    topics_collection = db["topics"]
    doc = await topics_collection.find_one({
        "subject": subject,
        "topic": topic
    })
    return doc["questions"] if doc else []


async def save_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Сохранить или обновить пользователя"""
    db = await get_db()
    users_collection = db["users"]
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "last_active": datetime.now()
        }},
        upsert=True
    )


async def save_test_session(user_id: int, subject: str, topic: str, questions_data: list):
    """Сохранить сессию тестирования с перемешанными вариантами ответов"""
    db = await get_db()
    sessions_collection = db["test_sessions"]
    
    # Удаляем старую незавершенную сессию пользователя
    await sessions_collection.delete_many({
        "user_id": user_id,
        "completed_at": None
    })
    
    prepared_questions = []
    for q in questions_data:
        q_copy = q.copy()
        
        if q_copy.get('type') != 'full_answer':
            options = q_copy.get('options', [])
            if options:
                correct_option_index = q_copy.get('correct_option', 0)
                correct_answer_text = options[correct_option_index] if correct_option_index < len(options) else None
                
                if correct_answer_text:
                    shuffled_options = options.copy()
                    random.shuffle(shuffled_options)
                    
                    new_correct_index = shuffled_options.index(correct_answer_text)
                    
                    q_copy['shuffled_options'] = shuffled_options
                    q_copy['correct'] = new_correct_index
        
        prepared_questions.append(q_copy)
    
    session = {
        "user_id": user_id,
        "subject": subject,
        "topic": topic,
        "questions": prepared_questions,
        "current_question": 0,
        "score": 0,
        "user_answers": [],
        "started_at": datetime.now(),
        "completed_at": None
    }
    
    result = await sessions_collection.insert_one(session)
    print(f"✅ Создана сессия для пользователя {user_id}: {subject} - {topic}")
    return result.inserted_id


async def get_test_session(user_id: int):
    """Получить активную сессию тестирования"""
    db = await get_db()
    sessions_collection = db["test_sessions"]
    return await sessions_collection.find_one({
        "user_id": user_id,
        "completed_at": None
    })


async def update_test_session(user_id: int, update_data: dict):
    """Обновить сессию тестирования"""
    db = await get_db()
    sessions_collection = db["test_sessions"]
    
    result = await sessions_collection.update_one(
        {"user_id": user_id, "completed_at": None},
        {"$set": update_data}
    )
    return result


async def complete_test_session(user_id: int):
    """Завершить сессию тестирования"""
    db = await get_db()
    sessions_collection = db["test_sessions"]
    await sessions_collection.update_one(
        {"user_id": user_id, "completed_at": None},
        {"$set": {"completed_at": datetime.now()}}
    )


async def save_test_result(user_id: int, subject: str, topic: str, score: int, total: int, 
                           percentage: float, grade: str, user_answers: list):
    """Сохранить результат тестирования в историю"""
    db = await get_db()
    results_collection = db["results"]
    await results_collection.insert_one({
        "user_id": user_id,
        "subject": subject,
        "topic": topic,
        "score": score,
        "total": total,
        "percentage": percentage,
        "grade": grade,
        "user_answers": user_answers,
        "completed_at": datetime.now()
    })


async def get_user_stats(user_id: int):
    """Получить статистику пользователя"""
    db = await get_db()
    results_collection = db["results"]
    cursor = results_collection.find({"user_id": user_id})
    results = await cursor.to_list(length=None)
    
    if not results:
        return None
    
    total_tests = len(results)
    avg_percentage = sum(r["percentage"] for r in results) / total_tests
    
    best_result = max(results, key=lambda x: x["percentage"]) if results else None
    
    return {
        "total_tests": total_tests,
        "avg_percentage": avg_percentage,
        "best_result": best_result
    }


async def get_completed_test_session(session_id: str):
    """Получить завершенную сессию тестирования по ID"""
    db = await get_db()
    sessions_collection = db["test_sessions"]
    return await sessions_collection.find_one({"_id": session_id})


async def get_last_completed_session(user_id: int):
    """Получить последнюю завершенную сессию пользователя"""
    db = await get_db()
    sessions_collection = db["test_sessions"]
    return await sessions_collection.find_one(
        {"user_id": user_id, "completed_at": {"$ne": None}},
        sort=[("completed_at", -1)]
    )