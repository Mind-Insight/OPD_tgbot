# app/handlers/review.py
from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.keyboards import get_review_keyboard, get_result_inline_keyboard
from app.database import get_completed_test_session, get_last_completed_session
from app.states import TestStates

router = Router()


async def format_review_message(session: dict) -> str:
    """Форматирует сообщение с разбором теста"""
    
    questions = session.get("questions", [])
    user_answers = session.get("user_answers", [])
    
    if not user_answers:
        return "❌ Нет данных для отображения разбора."
    
    total = len(questions)
    score = session.get("score", 0)
    
    review_text = f"📋 *Разбор теста*\n\n"
    review_text += f"📚 {session.get('subject')} - {session.get('topic')}\n"
    review_text += f"📊 Результат: {score}/{total} ({score/total*100:.1f}%)\n\n"
    review_text += f"{'='*40}\n\n"
    
    for i, (q, answer_data) in enumerate(zip(questions, user_answers), 1):
        # Эмодзи статуса
        if answer_data.get('is_correct'):
            status = "✅"
        else:
            status = "❌"
        
        # Ограничиваем длину вопроса
        question_text = q['text']
        if len(question_text) > 100:
            question_text = question_text[:97] + "..."
        
        review_text += f"*{status} Вопрос {i}/{total}:*\n"
        review_text += f"{question_text}\n\n"
        
        if q.get('type') == 'full_answer':
            # Развернутый вопрос
            review_text += f"📝 *Ваш ответ:*\n"
            user_ans = answer_data.get('user_answer', 'Нет ответа')
            if len(user_ans) > 200:
                user_ans = user_ans[:197] + "..."
            review_text += f"_{user_ans}_\n\n"
            
            if not answer_data.get('is_correct'):
                review_text += f"✅ *Правильный ответ:*\n"
                correct_ans = answer_data.get('correct_answer', 'Не указан')
                if len(correct_ans) > 200:
                    correct_ans = correct_ans[:197] + "..."
                review_text += f"_{correct_ans}_\n\n"
                
                if answer_data.get('keywords'):
                    review_text += f"💡 *Ключевые слова:* {', '.join(answer_data['keywords'])}\n\n"
        else:
            # Тестовый вопрос
            user_choice = answer_data.get('user_answer', 'Не выбран')
            correct_answer = answer_data.get('correct_answer', 'Не указан')
            
            if answer_data.get('is_correct'):
                review_text += f"✅ *Ваш ответ:* {user_choice}\n\n"
            else:
                review_text += f"❌ *Ваш ответ:* {user_choice}\n"
                review_text += f"✅ *Правильный ответ:* {correct_answer}\n\n"
        
        review_text += f"{'─'*40}\n\n"
    
    return review_text


@router.callback_query(lambda c: c.data == "review_test")
async def review_test(callback_query: types.CallbackQuery, state: FSMContext):
    """Показать разбор теста"""
    
    user_id = callback_query.from_user.id
    
    # Пытаемся получить session_id из состояния
    data = await state.get_data()
    session_id = data.get("last_session_id")
    
    session = None
    
    if session_id:
        # Если есть ID в состоянии, ищем по нему
        from bson import ObjectId
        try:
            session = await get_completed_test_session(ObjectId(session_id))
        except:
            pass
    
    if not session:
        # Если не нашли, ищем последнюю завершенную сессию
        session = await get_last_completed_session(user_id)
    
    if not session or not session.get("user_answers"):
        await callback_query.answer(
            "❌ Нет данных для отображения. Пройдите тест сначала!", 
            show_alert=True
        )
        return
    
    # Форматируем сообщение с разбором
    review_text = await format_review_message(session)
    
    # Отправляем сообщение
    if len(review_text) > 4000:
        parts = [review_text[i:i+4000] for i in range(0, len(review_text), 4000)]
        for idx, part in enumerate(parts):
            if idx == 0:
                await callback_query.message.answer(
                    part, 
                    parse_mode="Markdown", 
                    reply_markup=get_review_keyboard()
                )
            else:
                await callback_query.message.answer(part, parse_mode="Markdown")
    else:
        await callback_query.message.answer(
            review_text, 
            parse_mode="Markdown", 
            reply_markup=get_review_keyboard()
        )
    
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "back_to_results")
async def back_to_results(callback_query: types.CallbackQuery, state: FSMContext):
    """Вернуться к результатам теста"""
    
    user_id = callback_query.from_user.id
    
    # Получаем последнюю завершенную сессию
    session = await get_last_completed_session(user_id)
    
    if not session:
        await callback_query.answer("Ошибка!", show_alert=True)
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
    
    result_message = (
        f"🎉 Тестирование завершено!\n\n"
        f"📊 Результаты:\n"
        f"Предмет: {session.get('subject')}\n"
        f"Тема: {session.get('topic')}\n"
        f"Правильных ответов: {score}/{total}\n"
        f"Процент: {percentage:.1f}%\n"
        f"Оценка: {grade}"
    )
    
    await callback_query.message.answer(result_message)
    await callback_query.message.answer(
        "Что хотите сделать дальше?",
        reply_markup=get_result_inline_keyboard()
    )
    
    await callback_query.answer()