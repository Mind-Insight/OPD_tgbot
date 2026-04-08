# app/handlers/test.py
import asyncio
import random
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.states import TestStates
from app.keyboards import get_answers_keyboard, get_full_answer_keyboard, get_subjects_keyboard, get_result_inline_keyboard
from app.database import (
    get_test_session, update_test_session, complete_test_session,
    save_test_result, get_topics_by_subject, get_questions_by_topic,
    save_test_session
)

router = Router()

@router.message(TestStates.choosing_subject)
async def process_subject(message: types.Message, state: FSMContext):
    from app.keyboards import get_topics_keyboard
    from app.database import get_all_subjects
    
    subject = message.text
    
    if subject == "Отмена":
        from app.handlers.start import cmd_start
        await cmd_start(message, state)
        return
    
    subjects = await get_all_subjects()
    if subject not in subjects:
        await message.answer("Пожалуйста, выберите предмет из предложенных:")
        return
    
    await state.update_data(subject=subject)
    topics = await get_topics_by_subject(subject)
    keyboard = await get_topics_keyboard(topics)
    
    await message.answer(
        f"📚 Выбран предмет: {subject}\n\n"
        "Теперь выберите тему для тестирования:",
        reply_markup=keyboard
    )
    await state.set_state(TestStates.choosing_topic)

@router.message(TestStates.choosing_topic)
async def process_topic(message: types.Message, state: FSMContext):
    from app.keyboards import get_subjects_keyboard
    from app.database import get_topics_by_subject
    
    topic = message.text
    
    if topic == "Назад к предметам":
        await message.answer(
            "Выберите предмет:",
            reply_markup=get_subjects_keyboard()
        )
        await state.set_state(TestStates.choosing_subject)
        return
    
    data = await state.get_data()
    subject = data.get('subject')
    
    topics = await get_topics_by_subject(subject)
    if topic not in topics:
        await message.answer("Пожалуйста, выберите тему из предложенных:")
        return
    
    questions = await get_questions_by_topic(subject, topic)
    
    if not questions:
        await message.answer("В этой теме пока нет вопросов")
        return
    
    shuffled_questions = questions.copy()
    random.shuffle(shuffled_questions)
    
    await save_test_session(
        user_id=message.from_user.id,
        subject=subject,
        topic=topic,
        questions_data=shuffled_questions
    )
    
    await start_test(message, state)


async def start_test(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
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
            reply_markup=get_full_answer_keyboard(),
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
            reply_markup=get_answers_keyboard(shuffled_options)
        )
        await state.set_state(TestStates.taking_test)


@router.message(TestStates.taking_test)
async def process_multiple_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    if text == "Отменить тестирование":
        from app.handlers.start import cmd_start
        await complete_test_session(user_id)
        await state.clear()
        await message.answer(
            "Тестирование отменено. Используйте /start чтобы начать заново.",
            reply_markup=None
        )
        await cmd_start(message, state)
        return
    
    session = await get_test_session(user_id)
    if not session:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    current_index = session.get("current_question", 0)
    questions = session.get("questions", [])
    current_question_data = questions[current_index]
    
    try:
        user_answer_num = int(text.split('.')[0]) - 1
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите ответ из предложенных вариантов:")
        return
    
    shuffled_options = current_question_data.get('shuffled_options', [])
    if user_answer_num < 0 or user_answer_num >= len(shuffled_options):
        await message.answer("Пожалуйста, выберите ответ из предложенных вариантов:")
        return
    
    if user_answer_num == current_question_data.get('correct', -1):
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
        'user_answer': shuffled_options[user_answer_num],
        'correct_answer': shuffled_options[current_question_data.get('correct', -1)],
        'is_correct': is_correct,
        'type': 'multiple_choice'
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


@router.message(TestStates.waiting_for_answer)
async def process_full_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    
    if text == "Отменить тестирование":
        from app.handlers.start import cmd_start
        await complete_test_session(user_id)
        await state.clear()
        await message.answer(
            "Тестирование отменено. Используйте /start чтобы начать заново.",
            reply_markup=None
        )
        await cmd_start(message, state)
        return
    
    session = await get_test_session(user_id)
    if not session:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    current_index = session.get("current_question", 0)
    questions = session.get("questions", [])
    current_question_data = questions[current_index]
    
    if text == "Пропустить вопрос":
        feedback = "⏭ Вопрос пропущен."
        is_correct = False
        user_answer_text = "Не ответил"
        score_earned = 0
    else:
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
        
        user_answer_text = text
    
    user_answers = session.get("user_answers", [])
    user_answers.append({
        'question': current_question_data['text'],
        'user_answer': user_answer_text,
        'correct_answer': current_question_data.get('correct_answer', 'Не указан'),
        'is_correct': is_correct,
        'type': 'full_answer',
        'score_earned': score_earned
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
    user_id = message.from_user.id
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
    
    await message.answer(result_message, reply_markup=None)
    
    await message.answer(
        "Что хотите сделать дальше?",
        reply_markup=get_result_inline_keyboard()
    )
    
    await state.set_state(TestStates.choosing_subject)

@router.callback_query(lambda c: c.data == "show_stats")
async def show_stats_callback(callback_query: types.CallbackQuery, state: FSMContext):
    from app.handlers.stats import show_stats
    await show_stats(callback_query.message, state)
    await callback_query.answer()

@router.callback_query(lambda c: c.data == "new_test")
async def new_test_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()