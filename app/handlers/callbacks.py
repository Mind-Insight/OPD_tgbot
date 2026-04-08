
from . import review
# app/handlers/callbacks.py
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.keyboards import (
    get_subjects_keyboard, get_topics_keyboard, get_result_inline_keyboard,
    SUBJECTS
)
from app.database import (
    get_test_session, update_test_session, complete_test_session,
    save_test_result, get_topics_by_subject, get_questions_by_topic,
    save_test_session, get_user_stats, get_db
)
from app.states import TestStates
from app.handlers.exam import start_test, finish_test
from datetime import datetime
import random

router = Router()


# ==================== ВЫБОР ПРЕДМЕТА И ТЕМЫ ====================

@router.callback_query(lambda c: c.data.startswith("subject_"))
async def process_subject(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора предмета"""
    
    subject_id = int(callback_query.data.replace("subject_", ""))
    subject = SUBJECTS.get(subject_id)
    
    if not subject:
        await callback_query.answer("Предмет не найден", show_alert=True)
        return
    
    from app.database import get_all_subjects
    subjects = await get_all_subjects()
    
    if subject not in subjects:
        await callback_query.answer("Предмет не найден", show_alert=True)
        return
    
    await state.update_data(subject=subject, subject_id=subject_id)
    topics = await get_topics_by_subject(subject)
    keyboard = await get_topics_keyboard(topics, subject_id)
    
    await callback_query.message.edit_text(
        f"📚 Выбран предмет: {subject}\n\n"
        "Теперь выберите тему для тестирования:",
        reply_markup=keyboard
    )
    await state.set_state(TestStates.choosing_topic)
    await callback_query.answer()


@router.callback_query(lambda c: c.data.startswith("topic_"))
async def process_topic(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора темы"""
    
    data = callback_query.data.replace("topic_", "")
    parts = data.split("_")
    subject_id = int(parts[0])
    topic_idx = int(parts[1])
    
    subject = SUBJECTS.get(subject_id)
    
    if not subject:
        await callback_query.answer("Предмет не найден", show_alert=True)
        return
    
    topics = await get_topics_by_subject(subject)
    
    if topic_idx >= len(topics):
        await callback_query.answer("Тема не найдена", show_alert=True)
        return
    
    real_topic = topics[topic_idx]
    questions = await get_questions_by_topic(subject, real_topic)
    
    if not questions:
        await callback_query.answer("В этой теме пока нет вопросов", show_alert=True)
        return
    
    shuffled_questions = questions.copy()
    random.shuffle(shuffled_questions)
    
    await save_test_session(
        user_id=callback_query.from_user.id,
        subject=subject,
        topic=real_topic,
        questions_data=shuffled_questions
    )
    
    await callback_query.message.delete()
    await start_test(callback_query.message, state)
    await callback_query.answer()


# ==================== НАВИГАЦИЯ ====================

@router.callback_query(lambda c: c.data == "back_to_subjects")
async def back_to_subjects(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору предмета"""
    
    await callback_query.message.edit_text(
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "cancel")
async def cancel_main(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена из главного меню"""
    
    await state.clear()
    await callback_query.message.edit_text(
        "👋 Добро пожаловать в бот для тестирования!\n\n"
        "Выберите предмет для начала тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "new_test")
async def new_test_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Новый тест после завершения"""
    
    await callback_query.message.answer(
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()


# ==================== ПРОДОЛЖЕНИЕ ТЕСТА ====================

@router.callback_query(lambda c: c.data == "continue_test")
async def continue_test(callback_query: types.CallbackQuery, state: FSMContext):
    """Продолжить незавершенный тест"""
    
    user_id = callback_query.from_user.id
    session = await get_test_session(user_id)
    
    if session:
        await callback_query.message.delete()
        await start_test(callback_query.message, state)
    else:
        await callback_query.message.edit_text(
            "Не найден незавершенный тест.\n\n"
            "Выберите предмет для тестирования:",
            reply_markup=get_subjects_keyboard()
        )
        await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "start_new_test")
async def start_new_test(callback_query: types.CallbackQuery, state: FSMContext):
    """Начать новый тест (отменить незавершенный)"""
    
    user_id = callback_query.from_user.id
    await complete_test_session(user_id)
    await callback_query.message.edit_text(
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()


# ==================== ОТВЕТЫ НА ТЕСТЫ ====================

@router.callback_query(lambda c: c.data.startswith("answer_"))
async def process_multiple_choice(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик ответов на вопросы с вариантами"""
    
    user_id = callback_query.from_user.id
    _, q_idx, opt_idx = callback_query.data.split("_")
    q_idx = int(q_idx)
    opt_idx = int(opt_idx)
    
    session = await get_test_session(user_id)
    if not session:
        await callback_query.answer("Ошибка! Начните тестирование заново", show_alert=True)
        await state.clear()
        return
    
    questions = session.get("questions", [])
    if q_idx >= len(questions):
        await callback_query.answer("Ошибка! Вопрос не найден", show_alert=True)
        return
    
    current_question_data = questions[q_idx]
    shuffled_options = current_question_data.get('shuffled_options', [])
    
    if opt_idx >= len(shuffled_options):
        await callback_query.answer("Ошибка! Вариант не найден", show_alert=True)
        return
    
    if opt_idx == current_question_data.get('correct', -1):
        score_earned = 1
        feedback = "✅ Правильно!"
        is_correct = True
    else:
        score_earned = 0
        correct_answer_text = shuffled_options[current_question_data.get('correct', -1)]
        feedback = f"❌ Неправильно. Правильный ответ: {correct_answer_text}"
        is_correct = False
    
    user_answers = session.get("user_answers", [])
    user_answers.append({
        'question': current_question_data['text'],
        'user_answer': shuffled_options[opt_idx],
        'correct_answer': shuffled_options[current_question_data.get('correct', -1)],
        'is_correct': is_correct,
        'type': 'multiple_choice'
    })
    
    current_score = session.get("score", 0) + score_earned

    await update_test_session(user_id, {
        "current_question": q_idx + 1,
        "score": current_score,
        "user_answers": user_answers
    })
    
    await callback_query.answer(feedback, show_alert=False)
    await callback_query.message.delete()
    await start_test(callback_query.message, state)


@router.callback_query(lambda c: c.data.startswith("skip_"))
async def skip_question(callback_query: types.CallbackQuery, state: FSMContext):
    """Пропустить вопрос"""
    
    user_id = callback_query.from_user.id
    _, q_idx = callback_query.data.split("_")
    q_idx = int(q_idx)
    
    session = await get_test_session(user_id)
    if not session:
        await callback_query.answer("Ошибка!", show_alert=True)
        return
    
    user_answers = session.get("user_answers", [])
    questions = session.get("questions", [])
    
    user_answers.append({
        'question': questions[q_idx]['text'],
        'user_answer': "Пропущено",
        'correct_answer': questions[q_idx].get('correct_answer', 'Не указан'),
        'is_correct': False,
        'type': 'full_answer',
        'score_earned': 0
    })
    
    await update_test_session(user_id, {
        "current_question": q_idx + 1,
        "user_answers": user_answers
    })
    
    await callback_query.answer("⏭ Вопрос пропущен", show_alert=False)
    await callback_query.message.delete()
    await start_test(callback_query.message, state)


@router.callback_query(lambda c: c.data == "cancel_test")
async def cancel_test(callback_query: types.CallbackQuery, state: FSMContext):
    """Отменить тестирование"""
    
    user_id = callback_query.from_user.id
    await complete_test_session(user_id)
    await state.clear()
    await callback_query.message.answer(
        "Тестирование отменено.\n\n"
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()


# ==================== СТАТИСТИКА ====================

@router.callback_query(lambda c: c.data == "show_stats")
async def show_stats_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Показать статистику"""
    
    from app.handlers.stats import show_stats
    await show_stats(callback_query.message, state)
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "detailed_stats")
async def detailed_stats(callback_query: types.CallbackQuery):
    """Детальная статистика (последние 10 тестов)"""
    
    db = await get_db()
    results_collection = db["results"]
    cursor = results_collection.find(
        {"user_id": callback_query.from_user.id}
    ).sort("completed_at", -1).limit(10)
    results = await cursor.to_list(length=None)
    
    if not results:
        await callback_query.message.answer("📊 Нет результатов")
        await callback_query.answer()
        return
    
    text = "📋 *Последние 10 результатов:*\n\n"
    for i, r in enumerate(results, 1):
        date = r.get('completed_at', datetime.now()).strftime("%d.%m.%Y")
        text += f"{i}. *{r['subject']}* - {r['topic']}\n"
        text += f"   {r['score']}/{r['total']} ({r['percentage']:.0f}%) — 📅 {date}\n\n"
    
    await callback_query.message.answer(text, parse_mode="Markdown")
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "quick_new_test")
async def quick_new_test(callback_query: types.CallbackQuery, state: FSMContext):
    """Быстрый новый тест из статистики"""
    
    await callback_query.message.answer(
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()