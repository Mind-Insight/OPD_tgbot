# app/handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.database import get_test_session, save_user
from app.keyboards import get_subjects_keyboard
from app.states import TestStates

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    await save_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Проверяем, есть ли незавершенный тест
    active_session = await get_test_session(user_id)
    if active_session:
        await message.answer(
            "🔄 Обнаружен незавершенный тест! Хотите продолжить?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Продолжить тест")],
                    [KeyboardButton(text="❌ Начать новый")]
                ],
                resize_keyboard=True
            )
        )
        return
    
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в бот для тестирования!\n\n"
        "Выберите предмет для начала тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)

@router.message(lambda message: message.text == "✅ Продолжить тест")
async def continue_test(message: types.Message, state: FSMContext):
    from app.handlers.test import start_test
    user_id = message.from_user.id
    session = await get_test_session(user_id)
    
    if session:
        await start_test(message, state)
    else:
        await message.answer("Не найден незавершенный тест. Начните новый с /start")
        await cmd_start(message, state)

@router.message(lambda message: message.text == "❌ Начать новый")
async def start_new_test(message: types.Message, state: FSMContext):
    from app.database import complete_test_session
    user_id = message.from_user.id
    await complete_test_session(user_id)
    await cmd_start(message, state)