from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart


router = Router()


enter_url_tabl = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Начать аналитику')]
    ], resize_keyboard=True
)

@router.message(CommandStart())
async def start(message: Message):
    await message.answer('Привет!', reply_markup=enter_url_tabl)


@router.message(F.text == 'Начать аналитику')
async def ask_for_link(message: Message):
    await message.answer('Отправьте мне ссылку на Google Таблицу, и я выведу информацию')


@router.message(F.text.contains('docs.google.com/spreadsheets') | F.text.endswith('.csv'))
async def handle_table_url(message: Message):
    await message.answer('Ссылка принята! Формат подходит, начинаю анализ данных...')


@router.message(F.text.startswith('http'))
async def handle_url(message: Message):
    await message.answer('Пришли коректную ссылку для анализа')