# app/keyboards.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Словарь соответствия предметов и ID
SUBJECTS = {
    1: "Матанализ",
    2: "Линейная алгебра", 
    3: "Системное администрирование",
    4: "Информатика",
    5: "Английский язык"
}

# Обратный словарь
SUBJECTS_BY_ID = {v: k for k, v in SUBJECTS.items()}


def get_subjects_keyboard():
    """Inline-клавиатура с выбором предмета"""
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Матанализ", callback_data="subject_1")],
        [InlineKeyboardButton(text="📐 Линейная алгебра", callback_data="subject_2")],
        [InlineKeyboardButton(text="💻 Системное администрирование", callback_data="subject_3")],
        [InlineKeyboardButton(text="🧠 Информатика", callback_data="subject_4")],
        [InlineKeyboardButton(text="🇬🇧 Английский язык", callback_data="subject_5")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])


async def get_topics_keyboard(topics: list, subject_id: int):
    """Динамическая inline-клавиатура для выбора темы"""
    
    keyboard_buttons = []
    
    for idx, topic in enumerate(topics):
        keyboard_buttons.append([
            InlineKeyboardButton(text=topic, callback_data=f"topic_{subject_id}_{idx}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад к предметам", callback_data="back_to_subjects")])
    keyboard_buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_answers_keyboard(options: list, question_index: int):
    """Inline-клавиатура для ответов на вопросы с вариантами"""
    
    keyboard_buttons = []
    
    for i, option in enumerate(options):
        display_text = f"{i + 1}. {option[:50] + '...' if len(option) > 50 else option}"
        keyboard_buttons.append([
            InlineKeyboardButton(text=display_text, callback_data=f"answer_{question_index}_{i}")
        ])
    
    keyboard_buttons.append([InlineKeyboardButton(text="❌ Отменить тестирование", callback_data="cancel_test")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_full_answer_keyboard(question_index: int):
    """Inline-клавиатура для вопросов с полным ответом"""
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить вопрос", callback_data=f"skip_{question_index}")],
        [InlineKeyboardButton(text="❌ Отменить тестирование", callback_data="cancel_test")]
    ])


def get_result_inline_keyboard():
    """Inline-клавиатура после завершения теста"""
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Посмотреть разбор теста", callback_data="review_test")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="📋 Новый тест", callback_data="new_test")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_subjects")]
    ])


def get_review_keyboard():
    """Inline-клавиатура для окна просмотра результатов"""
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться к результатам", callback_data="back_to_results")],
        [InlineKeyboardButton(text="📋 Новый тест", callback_data="new_test")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_subjects")]
    ])


def get_continue_test_keyboard():
    """Inline-клавиатура для продолжения теста"""
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Продолжить тест", callback_data="continue_test")],
        [InlineKeyboardButton(text="❌ Начать новый", callback_data="start_new_test")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_subjects")]
    ])


def get_stats_inline_keyboard():
    """Inline-клавиатура для статистики"""
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Детальная статистика", callback_data="detailed_stats")],
        [InlineKeyboardButton(text="🚀 Новый тест", callback_data="quick_new_test")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_subjects")]
    ])