# app/handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.database import get_test_session, save_user, complete_test_session
from app.keyboards import get_subjects_keyboard, get_continue_test_keyboard
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
            "🔄 Обнаружен незавершенный тест!\n\n"
            "Выберите действие:",
            reply_markup=get_continue_test_keyboard()
        )
        return
    
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в бот для тестирования!\n\n"
        "Выберите предмет для начала тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)


# Обработчик кнопки "Отмена"
@router.callback_query(lambda c: c.data == "cancel")
async def cancel_action(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.answer(
        "👋 Добро пожаловать в бот для тестирования!\n\n"
        "Выберите предмет для начала тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()