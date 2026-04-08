


@dp.callback_query(lambda c: c.data == "show_stats")
async def process_stats_callback(callback_query: types.CallbackQuery):
    stats = await get_user_stats(callback_query.from_user.id)

    if not stats:
        await callback_query.message.answer(
            "📊 У вас пока нет пройденных тестов.\n"
            "Выберите предмет и тему, чтобы начать тестирование!"
        )
    else:
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

        await callback_query.message.answer(stats_text, parse_mode="Markdown")

    await callback_query.answer()


@dp.callback_query(lambda c: c.data == "new_test")
async def process_new_test_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Выберите предмет для тестирования:",
        reply_markup=get_subjects_keyboard()
    )
    await state.set_state(TestStates.choosing_subject)
    await callback_query.answer()