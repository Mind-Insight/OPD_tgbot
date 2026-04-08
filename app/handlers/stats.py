# app/handlers/stats.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.keyboards import get_subjects_keyboard, get_stats_inline_keyboard
from app.database import get_user_stats, get_db
from app.states import TestStates
from datetime import datetime

router = Router()


@router.message(Command("stats"))
@router.callback_query(lambda c: c.data == "show_stats")
async def show_stats(event: types.Message | types.CallbackQuery, state: FSMContext):
    # Определяем, откуда пришел вызов
    if isinstance(event, types.CallbackQuery):
        message = event.message
        user_id = event.from_user.id
        await event.answer()
    else:
        message = event
        user_id = event.from_user.id
    
    stats = await get_user_stats(user_id)
    
    if not stats:
        await message.answer(
            "📊 У вас пока нет пройденных тестов.\n\n"
            "Выберите предмет для начала тестирования:",
            reply_markup=get_subjects_keyboard()
        )
        await state.set_state(TestStates.choosing_subject)
        return
    
    stats_text = (
        f"📊 *Ваша статистика:*\n\n"
        f"📝 Пройдено тестов: {stats['total_tests']}\n"
        f"📈 Средний результат: {stats['avg_percentage']:.1f}%\n"
    )
    
    if stats['best_result']:
        stats_text += (
            f"\n🏆 *Лучший результат:*\n"
            f"📚 {stats['best_result']['subject']} - {stats['best_result']['topic']}\n"
            f"📊 {stats['best_result']['percentage']:.1f}%"
        )
    
    await message.answer(stats_text, parse_mode="Markdown", reply_markup=get_stats_inline_keyboard())


@router.callback_query(lambda c: c.data == "detailed_stats")
async def detailed_stats(callback_query: types.CallbackQuery):
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
    await callback_query.message.answer(
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()


@router.callback_query(lambda c: c.data == "back_to_subjects")
async def back_to_subjects(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()