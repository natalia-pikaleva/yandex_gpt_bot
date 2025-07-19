from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_for_book_selection = State()
    waiting_for_question = State()


class DownloadStates(StatesGroup):
    waiting_for_oauth = State()
    waiting_for_path = State()
    waiting_for_confirm = State()
