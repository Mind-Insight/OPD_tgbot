# app/handlers/stats.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.keyboards import get_stats_inline_keyboard, get_subjects_keyboard
from app.database import get_user_stats
from app.states import TestStates
from datetime import datetime

router = Router()

@router.message(Command("stats"))
@router.message(lambda message: message.text == "📊 Моя статистика")
async def show_stats(message: types.Message, state: FSMContext):
    stats = await get_user_stats(message.from_user.id)
    
    if not stats:
        await message.answer(
            "📊 *У вас пока нет пройденных тестов*\n\n"
            "Выберите предмет в меню ниже, чтобы начать тестирование!",
            parse_mode="Markdown"
        )
        return
    
    # Прогресс-бар
    avg = stats['avg_percentage']
    bar_length = 10
    filled = int(avg / 100 * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    stats_text = (
        f"📊 *Ваша статистика*\n\n"
        f"┌─────────────────────┐\n"
        f"│ Тестов пройдено: {stats['total_tests']:>3}        │\n"
        f"│ Средний результат: {avg:>5.1f}%        │\n"
        f"│ {bar} │\n"
        f"└─────────────────────┘\n"
    )
    
    if stats['best_result']:
        stats_text += (
            f"\n🏆 *Лучший результат*\n"
            f"┌─────────────────────┐\n"
            f"│ {stats['best_result']['subject'][:19]} │\n"
            f"│ {stats['best_result']['topic'][:19]} │\n"
            f"│ {stats['best_result']['percentage']:.1f}% ({stats['best_result']['score']}/{stats['best_result']['total']}) │\n"
            f"└─────────────────────┘\n"
        )
    
    await message.answer(stats_text, parse_mode="Markdown", reply_markup=get_stats_inline_keyboard())

@router.callback_query(lambda c: c.data == "detailed_stats")
async def detailed_stats(callback_query: types.CallbackQuery):
    from app.database import database
    
    results_collection = database["results"]
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