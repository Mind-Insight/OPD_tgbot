# app/handlers/test.py
import asyncio
import random
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.states import TestStates
from app.keyboards import (
    get_answers_keyboard, get_full_answer_keyboard, 
    get_subjects_keyboard, get_result_inline_keyboard
)
from app.database import (
    get_test_session, update_test_session, complete_test_session,
    save_test_result
)

router = Router()


async def start_test(message: types.Message, state: FSMContext):
    """Начать или продолжить тест"""
    
    user_id = message.chat.id
    session = await get_test_session(user_id)
    
    if not session:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    current_index = session.get("current_question", 0)
    questions = session.get("questions", [])
    total = len(questions)
    
    if current_index >= total:
        await finish_test(message, state)
        return

    current_question_data = questions[current_index]
    question_number = current_index + 1

    if current_question_data.get('type') == 'full_answer':
        await message.answer(
            f"📝 Вопрос {question_number}/{total} (развернутый ответ):\n\n"
            f"{current_question_data['text']}\n\n"
            f"💡 *Подсказка:* {current_question_data.get('hint', 'Постарайтесь дать развернутый и аргументированный ответ.')}\n\n"
            "Напишите ваш развернутый ответ ниже:",
            reply_markup=get_full_answer_keyboard(current_index),
            parse_mode="Markdown"
        )
        await state.set_state(TestStates.waiting_for_answer)
    else:
        options = current_question_data.get('options', [])
        correct_answer = options[current_question_data.get('correct_option', 0)]
        
        shuffled_options = options.copy()
        random.shuffle(shuffled_options)
        
        new_correct_index = shuffled_options.index(correct_answer)
        
        current_question_data['shuffled_options'] = shuffled_options
        current_question_data['correct'] = new_correct_index
        questions[current_index] = current_question_data
        
        await update_test_session(user_id, {
            "questions": questions
        })
        
        await message.answer(
            f"❓ Вопрос {question_number}/{total}:\n"
            f"{current_question_data['text']}",
            reply_markup=get_answers_keyboard(shuffled_options, current_index)
        )
        await state.set_state(TestStates.taking_test)


@router.message(TestStates.waiting_for_answer)
async def process_full_answer(message: types.Message, state: FSMContext):
    """Обработчик полных ответов"""
    
    user_id = message.from_user.id
    text = message.text
    
    session = await get_test_session(user_id)
    if not session:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    current_index = session.get("current_question", 0)
    questions = session.get("questions", [])
    current_question_data = questions[current_index]
    
    keywords = current_question_data.get('keywords', [])
    
    if keywords:
        user_answer_lower = text.lower()
        found_keywords = [kw for kw in keywords if kw.lower() in user_answer_lower]
        
        if len(found_keywords) >= len(keywords) * 0.6:
            score_earned = 1
            is_correct = True
            feedback = f"✅ Ответ принят! Вы упомянули ключевые моменты: {', '.join(found_keywords)}"
        else:
            score_earned = 0
            is_correct = False
            feedback = f"❌ Ответ неполный. Ожидалось упоминание: {', '.join(keywords)}"
    else:
        score_earned = 1
        is_correct = True
        feedback = "✅ Ответ принят!"
    
    user_answers = session.get("user_answers", [])
    
    # Сохраняем больше информации для разбора
    user_answers.append({
        'question': current_question_data['text'],
        'question_text': current_question_data['text'],
        'user_answer': text,
        'correct_answer': current_question_data.get('correct_answer', 'Не указан'),
        'is_correct': is_correct,
        'type': 'full_answer',
        'score_earned': score_earned,
        'hint': current_question_data.get('hint', ''),
        'keywords': keywords
    })
    
    current_score = session.get("score", 0) + score_earned
    
    await update_test_session(user_id, {
        "current_question": current_index + 1,
        "score": current_score,
        "user_answers": user_answers
    })
    
    await message.answer(feedback)
    await asyncio.sleep(1)
    await start_test(message, state)


async def finish_test(message: types.Message, state: FSMContext):
    """Завершение теста и сохранение результатов"""
    
    user_id = message.chat.id
    session = await get_test_session(user_id)
    
    if not session:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    # Сохраняем ID сессии перед завершением
    session_id = str(session["_id"])
    
    score = session.get("score", 0)
    total = len(session.get("questions", []))
    percentage = (score / total) * 100 if total > 0 else 0
    
    if percentage >= 90:
        grade = "5 (Отлично)"
    elif percentage >= 75:
        grade = "4 (Хорошо)"
    elif percentage >= 60:
        grade = "3 (Удовлетворительно)"
    else:
        grade = "2 (Неудовлетворительно)"
    
    user_answers = session.get("user_answers", [])
    
    await save_test_result(
        user_id=user_id,
        subject=session.get("subject"),
        topic=session.get("topic"),
        score=score,
        total=total,
        percentage=percentage,
        grade=grade,
        user_answers=user_answers
    )
    
    await complete_test_session(user_id)
    
    # Сохраняем session_id в состояние для последующего разбора
    await state.update_data(last_session_id=session_id)
    
    result_message = (
        f"🎉 Тестирование завершено!\n\n"
        f"📊 Результаты:\n"
        f"Предмет: {session.get('subject')}\n"
        f"Тема: {session.get('topic')}\n"
        f"Правильных ответов: {score}/{total}\n"
        f"Процент: {percentage:.1f}%\n"
        f"Оценка: {grade}"
    )
    
    await message.answer(result_message)
    await message.answer(
        "Что хотите сделать дальше?",
        reply_markup=get_result_inline_keyboard()
    )
    
    await state.set_state(TestStates.choosing_subject)
    """Завершение теста и сохранение результатов"""
    
    user_id = message.chat.id
    session = await get_test_session(user_id)
    
    if not session:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    score = session.get("score", 0)
    total = len(session.get("questions", []))
    percentage = (score / total) * 100 if total > 0 else 0
    
    if percentage >= 90:
        grade = "5 (Отлично)"
    elif percentage >= 75:
        grade = "4 (Хорошо)"
    elif percentage >= 60:
        grade = "3 (Удовлетворительно)"
    else:
        grade = "2 (Неудовлетворительно)"
    
    user_answers = session.get("user_answers", [])
    
    await save_test_result(
        user_id=user_id,
        subject=session.get("subject"),
        topic=session.get("topic"),
        score=score,
        total=total,
        percentage=percentage,
        grade=grade,
        user_answers=user_answers
    )
    
    await complete_test_session(user_id)
    
    result_message = (
        f"🎉 Тестирование завершено!\n\n"
        f"📊 Результаты:\n"
        f"Предмет: {session.get('subject')}\n"
        f"Тема: {session.get('topic')}\n"
        f"Правильных ответов: {score}/{total}\n"
        f"Процент: {percentage:.1f}%\n"
        f"Оценка: {grade}"
    )
    
    await message.answer(result_message)
    await message.answer(
        "Что хотите сделать дальше?",
        reply_markup=get_result_inline_keyboard()
    )
    
    await state.set_state(TestStates.choosing_subject)