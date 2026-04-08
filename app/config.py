import os
from datetime import datetime

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

client = None
database = None


async def init_db():
    global client, database
    client = AsyncIOMotorClient(MONGO_URI)
    database = client[MONGO_DB_NAME]
    # print(database.users.find())
    async for i in database["users"].find({}):
        print(i)

    await client.admin.command('ping')
    print(f"✅ Подключено к MongoDB: {MONGO_DB_NAME}")

    await database.users.create_index("user_id", unique=True)
    await database.test_sessions.create_index("user_id")
    await database.results.create_index("user_id")

    return database


async def close_db():
    if client:
        client.close()


async def load_tests_from_dict(tests_database):
    """Загрузка тестов из словаря в MongoDB (только при первом запуске)"""
    topics_collection = database["topics"]

    if await topics_collection.count_documents({}) > 0:
        print("Тесты уже загружены, пропускаем")
        return

    print("Загрузка тестов в mongodb")

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
            print(
                f"  ✅ {subject_name} -> {topic_name} ({len(questions)} вопросов)")

    print("Все тесты загружены!")


async def get_all_subjects():
    """Получить список всех предметов"""
    topics_collection = database["topics"]
    subjects = await topics_collection.distinct("subject")
    return sorted(subjects)


async def get_topics_by_subject(subject: str):
    """Получить список тем по предмету"""
    topics_collection = database["topics"]
    cursor = topics_collection.find(
        {"subject": subject}, {"topic": 1, "_id": 0})
    topics = await cursor.to_list(length=None)
    return [t["topic"] for t in topics]


async def get_questions_by_topic(subject: str, topic: str):
    """Получить все вопросы по теме"""
    topics_collection = database["topics"]
    doc = await topics_collection.find_one({
        "subject": subject,
        "topic": topic
    })
    return doc["questions"] if doc else []


async def save_user(
        user_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None):
    """Сохранить или обновить пользователя"""
    users_collection = database["users"]
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


async def save_test_session(
        user_id: int,
        subject: str,
        topic: str,
        questions_data: list):
    """Сохранить сессию тестирования (чтобы можно было восстановить после перезапуска)"""
    sessions_collection = database["test_sessions"]

    # Удаляем старую незавершенную сессию пользователя
    await sessions_collection.delete_many({
        "user_id": user_id,
        "completed_at": None
    })

    session = {
        "user_id": user_id,
        "subject": subject,
        "topic": topic,
        "questions": questions_data,
        "current_question": 0,
        "score": 0,
        "user_answers": [],
        "started_at": datetime.now(),
        "completed_at": None
    }

    result = await sessions_collection.insert_one(session)
    return result.inserted_id


async def get_test_session(user_id: int):
    """Получить активную сессию тестирования"""
    sessions_collection = database["test_sessions"]
    return await sessions_collection.find_one({
        "user_id": user_id,
        "completed_at": None
    })


async def update_test_session(user_id: int, update_data: dict):
    """Обновить сессию тестирования"""
    sessions_collection = database["test_sessions"]

    result = await sessions_collection.update_one(
        {"user_id": user_id, "completed_at": None},
        {"$set": update_data}
    )
    return result


async def complete_test_session(user_id: int):
    """Завершить сессию тестирования"""
    sessions_collection = database["test_sessions"]
    await sessions_collection.update_one(
        {"user_id": user_id, "completed_at": None},
        {"$set": {"completed_at": datetime.now()}}
    )


async def save_test_result(
        user_id: int,
        subject: str,
        topic: str,
        score: int,
        total: int,
        percentage: float,
        grade: str,
        user_answers: list):
    """Сохранить результат тестирования в историю"""
    results_collection = database["results"]
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
    results_collection = database["results"]
    cursor = results_collection.find({"user_id": user_id})
    results = await cursor.to_list(length=None)

    if not results:
        return None

    total_tests = len(results)
    avg_percentage = sum(r["percentage"] for r in results) / total_tests

    return {
        "total_tests": total_tests,
        "avg_percentage": avg_percentage,
        "best_result": max(
            results,
            key=lambda x: x["percentage"]) if results else None
    }
