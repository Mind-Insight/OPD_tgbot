import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random
from tests import *

# Токен бота
BOT_TOKEN = "8417155009:AAErzLUUCizSkU58DWyrpClgJA6guqKOjJU"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния FSM
class TestStates(StatesGroup):
    choosing_subject = State()
    choosing_topic = State()
    taking_test = State()

# Хранение состояния пользователей
user_data = {}

# Клавиатура для выбора предмета
def get_subjects_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Матанализ")],
            [KeyboardButton(text="Линейная алгебра")],
            [KeyboardButton(text="Системное администрирование")],
            [KeyboardButton(text="Информатика")],
            [KeyboardButton(text="Английский язык")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Клавиатура для выбора темы
def get_topics_keyboard(subject):
    topics = list(tests_database[subject].keys())
    keyboard_buttons = []
    
    # Разбиваем темы на ряды по 2 кнопки
    for i in range(0, len(topics), 2):
        row = [KeyboardButton(text=topic) for topic in topics[i:i+2]]
        keyboard_buttons.append(row)
    
    keyboard_buttons.append([KeyboardButton(text="Назад к предметам")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

# Клавиатура для ответов на вопросы
def get_answers_keyboard(options):
    keyboard_buttons = []
    
    for i, option in enumerate(options, 1):
        keyboard_buttons.append([KeyboardButton(text=f"{i}. {option}")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в бот для тестирования!\n\n"
        "Выберите предмет для начала тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)

# Обработчик выбора предмета
@dp.message(TestStates.choosing_subject)
async def process_subject(message: types.Message, state: FSMContext):
    subject = message.text
    
    if subject == "Отмена":
        await state.clear()
        await message.answer(
            "Тестирование отменено. Используйте /start чтобы начать заново.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if subject not in tests_database:
        await message.answer("Пожалуйста, выберите предмет из предложенных:")
        return
    
    await state.update_data(subject=subject)
    await message.answer(
        f"📚 Выбран предмет: {subject}\n\n"
        "Теперь выберите тему для тестирования:",
        reply_markup=get_topics_keyboard(subject)
    )
    await state.set_state(TestStates.choosing_topic)

# Обработчик выбора темы
@dp.message(TestStates.choosing_topic)
async def process_topic(message: types.Message, state: FSMContext):
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
    
    if subject not in tests_database or topic not in tests_database[subject]:
        await message.answer("Пожалуйста, выберите тему из предложенных:")
        return
    
    # Сохраняем данные теста для пользователя
    user_id = message.from_user.id # type: ignore
    user_data[user_id] = {
        'subject': subject,
        'topic': topic,
        'questions': tests_database[subject][topic].copy(),
        'current_question': 0,
        'score': 0,
        'total_questions': len(tests_database[subject][topic])
    }
    
    # Перемешиваем вопросы
    random.shuffle(user_data[user_id]['questions'])

    await start_test(message, state)

# Начало теста
async def start_test(message: types.Message, state: FSMContext):
    user_id = message.from_user.id # type: ignore
    if user_id not in user_data:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    test_data = user_data[user_id]
    
    if test_data['current_question'] >= test_data['total_questions']:
        await finish_test(message, state)
        return

    current_question_data = test_data['questions'][test_data['current_question']]
    question_number = test_data['current_question'] + 1

    current_answer = current_question_data['options'][current_question_data['correct']]
    random.shuffle(current_question_data['options'])
    for i in range(len(current_question_data['options'])):
        if current_question_data['options'][i] == current_answer:
            current_question_data['correct'] = i
            break

    await message.answer(
        f"❓ Вопрос {question_number}/{test_data['total_questions']}:\n"
        f"{current_question_data['question']}",
        reply_markup=get_answers_keyboard(current_question_data['options'])
    )
    await state.set_state(TestStates.taking_test)

# Обработчик ответов на вопросы
@dp.message(TestStates.taking_test)
async def process_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id # type: ignore
    if user_id not in user_data:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    test_data = user_data[user_id]
    current_question_data = test_data['questions'][test_data['current_question']]
    
    # Парсим ответ пользователя
    try:
        user_answer = int(message.text.split('.')[0]) - 1 # type: ignore
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите ответ из предложенных вариантов:")
        return
    
    # Проверяем ответ
    if user_answer == current_question_data['correct']:
        test_data['score'] += 1
        feedback = "✅ Правильно!"
    else:
        correct_answer = current_question_data['options'][current_question_data['correct']]
        feedback = f"❌ Неправильно. Правильный ответ: {correct_answer}"
    
    # Переходим к следующему вопросу
    test_data['current_question'] += 1
    
    if test_data['current_question'] < test_data['total_questions']:
        await message.answer(feedback)
        await asyncio.sleep(1)  # Пауза перед следующим вопросом
        await start_test(message, state)
    else:
        await message.answer(feedback)
        await asyncio.sleep(1)
        await finish_test(message, state)

# Завершение теста
async def finish_test(message: types.Message, state: FSMContext):
    user_id = message.from_user.id # type: ignore
    if user_id not in user_data:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    test_data = user_data[user_id]
    score = test_data['score']
    total = test_data['total_questions']
    percentage = (score / total) * 100
    
    # Определяем оценку
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
        f"Предмет: {test_data['subject']}\n"
        f"Тема: {test_data['topic']}\n"
        f"Правильных ответов: {score}/{total}\n"
        f"Процент: {percentage:.1f}%\n"
        f"Оценка: {grade}"
    )
    
    await message.answer(result_message, reply_markup=ReplyKeyboardRemove())
    
    # Предлагаем пройти ещё тест
    await message.answer(
        "Хотите пройти ещё один тест?",
        reply_markup=get_subjects_keyboard()
    )
    
    # Очищаем данные пользователя
    if user_id in user_data:
        del user_data[user_id]
    
    await state.set_state(TestStates.choosing_subject)

# Обработчик любых других сообщений
@dp.message()
async def any_message(message: types.Message):
    await message.answer(
        "Используйте /start чтобы начать тестирование или выберите команду из меню."
    )

# Основная функция
async def main():
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())