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
    waiting_for_answer = State()

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

# Клавиатура для ответов на вопросы с вариантами (с кнопкой отмены)
def get_answers_keyboard(options):
    keyboard_buttons = []
    
    for i, option in enumerate(options, 1):
        keyboard_buttons.append([KeyboardButton(text=f"{i}. {option}")])
    
    # Добавляем кнопку отмены тестирования
    keyboard_buttons.append([KeyboardButton(text="Отменить тестирование")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)

# Клавиатура для вопросов с полным ответом
def get_full_answer_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить вопрос")],
            [KeyboardButton(text="Отменить тестирование")]
        ],
        resize_keyboard=True
    )

# Функция для отмены тестирования
async def cancel_testing(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    await message.answer(
        "Тестирование отменено. Используйте /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    # Очищаем данные пользователя
    if user_id in user_data:
        del user_data[user_id]

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
        await cancel_testing(message, state)
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
    user_id = message.from_user.id
    user_data[user_id] = {
        'subject': subject,
        'topic': topic,
        'questions': tests_database[subject][topic].copy(),
        'current_question': 0,
        'score': 0,
        'total_questions': len(tests_database[subject][topic]),
        'user_answers': []  # Для хранения ответов пользователя
    }
    
    # Перемешиваем вопросы
    random.shuffle(user_data[user_id]['questions'])

    await start_test(message, state)

# Начало теста
async def start_test(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
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

    # Определяем тип вопроса
    if 'type' in current_question_data and current_question_data['type'] == 'full_answer':
        # Вопрос с полным ответом
        await message.answer(
            f"📝 Вопрос {question_number}/{test_data['total_questions']} (развернутый ответ):\n\n"
            f"{current_question_data['question']}\n\n"
            f"💡 *Подсказка:* {current_question_data.get('hint', 'Постарайтесь дать развернутый и аргументированный ответ.')}\n\n"
            "Напишите ваш развернутый ответ ниже:",
            reply_markup=get_full_answer_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(TestStates.waiting_for_answer)
    else:
        # Вопрос с выбором ответа
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

# Обработчик ответов на вопросы с вариантами
@dp.message(TestStates.taking_test)
async def process_multiple_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    text = message.text
    
    # Проверяем, не хочет ли пользователь отменить тестирование
    if text == "Отменить тестирование":
        await cancel_testing(message, state)
        return
    
    test_data = user_data[user_id]
    current_question_data = test_data['questions'][test_data['current_question']]
    
    # Парсим ответ пользователя
    try:
        user_answer = int(text.split('.')[0]) - 1
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите ответ из предложенных вариантов:")
        return
    
    # Проверяем корректность выбранного варианта
    if user_answer < 0 or user_answer >= len(current_question_data['options']):
        await message.answer("Пожалуйста, выберите ответ из предложенных вариантов:")
        return
    
    # Проверяем ответ
    if user_answer == current_question_data['correct']:
        test_data['score'] += 1
        feedback = "✅ Правильно!"
        is_correct = True
    else:
        correct_answer = current_question_data['options'][current_question_data['correct']]
        feedback = f"❌ Неправильно. Правильный ответ: {correct_answer}"
        is_correct = False
    
    # Сохраняем ответ пользователя
    test_data['user_answers'].append({
        'question': current_question_data['question'],
        'user_answer': current_question_data['options'][user_answer],
        'correct_answer': current_question_data['options'][current_question_data['correct']],
        'is_correct': is_correct,
        'type': 'multiple_choice'
    })
    
    # Переходим к следующему вопросу
    test_data['current_question'] += 1
    
    if test_data['current_question'] < test_data['total_questions']:
        await message.answer(feedback)
        await asyncio.sleep(1)
        await start_test(message, state)
    else:
        await message.answer(feedback)
        await asyncio.sleep(1)
        await finish_test(message, state)

# Обработчик полных ответов
@dp.message(TestStates.waiting_for_answer)
async def process_full_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_data:
        await message.answer("Ошибка! Начните тестирование заново с помощью /start")
        await state.clear()
        return
    
    text = message.text
    
    if text == "Отменить тестирование":
        await cancel_testing(message, state)
        return
    
    test_data = user_data[user_id]
    current_question_data = test_data['questions'][test_data['current_question']]
    
    if text == "Пропустить вопрос":
        feedback = "⏭ Вопрос пропущен."
        is_correct = False
        user_answer_text = "Не ответил"
        score_earned = 0
    else:
        # Проверяем ответ по ключевым словам
        correct_answer = current_question_data['correct_answer']
        keywords = current_question_data.get('keywords', [])
        
        if keywords:
            # Проверяем наличие ключевых слов в ответе
            user_answer_lower = text.lower()
            found_keywords = [kw for kw in keywords if kw.lower() in user_answer_lower]
            
            if len(found_keywords) >= len(keywords) * 0.6:  # 60% ключевых слов
                score_earned = 1
                test_data['score'] += score_earned
                is_correct = True
                feedback = f"✅ Ответ принят! Вы упомянули ключевые моменты: {', '.join(found_keywords)}"
            else:
                score_earned = 0
                is_correct = False
                feedback = f"❌ Ответ неполный. Ожидалось упоминание: {', '.join(keywords)}"
        else:
            # Если нет ключевых слов, всегда считаем правильным
            score_earned = 1
            test_data['score'] += score_earned
            is_correct = True
            feedback = "✅ Ответ принят!"
        
        user_answer_text = text
    
    # Сохраняем ответ пользователя
    test_data['user_answers'].append({
        'question': current_question_data['question'],
        'user_answer': user_answer_text,
        'correct_answer': current_question_data['correct_answer'],
        'is_correct': is_correct,
        'type': 'full_answer',
        'score_earned': score_earned
    })
    
    # Переходим к следующему вопросу
    test_data['current_question'] += 1
    
    if test_data['current_question'] < test_data['total_questions']:
        await message.answer(feedback)
        await asyncio.sleep(1)
        await start_test(message, state)
    else:
        await message.answer(feedback)
        await asyncio.sleep(1)
        await finish_test(message, state)

# Завершение теста
async def finish_test(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
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
    
    # Добавляем детализацию по ответам
    detail_message = "\n\n📝 Детализация ответов:\n"
    for i, answer_data in enumerate(test_data['user_answers'], 1):
        detail_message += f"\n{i}. "
        if answer_data['type'] == 'full_answer':
            detail_message += "📝 "
            status = "✅" if answer_data['is_correct'] else "❌"
        else:
            status = "✅" if answer_data['is_correct'] else "❌"
        
        # Обрезаем длинный вопрос для читаемости
        question_preview = answer_data['question'][:40] + "..." if len(answer_data['question']) > 40 else answer_data['question']
        detail_message += f"{question_preview} - {status}"
    
    await message.answer(result_message + detail_message, reply_markup=ReplyKeyboardRemove())
    
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