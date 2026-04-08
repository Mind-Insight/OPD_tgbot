from aiogram.fsm.state import State, StatesGroup


class TestStates(StatesGroup):
    """Состояния FSM"""

    choosing_subject = State()
    choosing_topic = State()
    taking_test = State()
    waiting_for_answer = State()