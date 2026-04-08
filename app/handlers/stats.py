# app/handlers/stats.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.database import get_user_stats

router = Router()


@router.message(Command("stats"))
@router.message(lambda message: message.text == "📊 Моя статистика")
async def show_stats(message: types.Message):
    stats = await get_user_stats(message.from_user.id)
    
    if not stats:
        await message.answer("📊 У вас пока нет пройденных тестов. Начните с /start!")
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
    
    await message.answer(stats_text, parse_mode="Markdown")