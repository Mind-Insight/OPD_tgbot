from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)


def get_subjects_keyboard():
    """Главная клавиатура с выбором предмета"""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Матанализ")],
            [KeyboardButton(text="Линейная алгебра")],
            [KeyboardButton(text="Системное администрирование")],
            [KeyboardButton(text="Информатика")],
            [KeyboardButton(text="Английский язык")],
            [KeyboardButton(text="📊 Моя статистика")],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True
    )


async def get_topics_keyboard(topics: list):
    """Динамическая клавиатура для выбора темы"""

    keyboard_buttons = []

    for i in range(0, len(topics), 2):
        row = [KeyboardButton(text=topic) for topic in topics[i:i + 2]]
        keyboard_buttons.append(row)

    keyboard_buttons.append([KeyboardButton(text="Назад к предметам")])

    return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)


def get_answers_keyboard(options):
    """Клавиатура для ответов на вопросы с вариантами"""

    keyboard_buttons = []

    for i, option in enumerate(options, 1):
        display_text = f"{i}. {option[:40] + '...' if len(option) > 40 else option}"
        keyboard_buttons.append([KeyboardButton(text=display_text)])

    keyboard_buttons.append([KeyboardButton(text="Отменить тестирование")])

    return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)


def get_full_answer_keyboard():
    """Клавиатура для вопросов с полным ответом"""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустить вопрос")],
            [KeyboardButton(text="Отменить тестирование")]
        ],
        resize_keyboard=True
    )


def get_stats_inline_keyboard():
    """Inline-клавиатура для статистики"""

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Детали", callback_data="detailed_stats")],
        [InlineKeyboardButton(text="🚀 Новый тест", callback_data="quick_new_test")]
    ])


def get_result_inline_keyboard():
    """Inline-клавиатура после завершения теста"""

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="📋 Новый тест", callback_data="new_test")]
    ])
