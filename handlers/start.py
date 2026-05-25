from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# Імпорт Pandas
import pandas as pd

from analytics import read_table_from_link

router = Router()

# Клавіатура
enter_url_tabl = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Інформація по даті')]
    ], resize_keyboard=True
)


# Стани (FSM)
class TableState(StatesGroup):
    waiting_for_link = State()  # Очікування посилання
    waiting_for_date = State()  # Очікування дати


# 1. Команда /start
@router.message(CommandStart())
async def start(message: Message):
    await message.answer('Привіт!', reply_markup=enter_url_tabl)


# 2. Натискання на кнопку
@router.message(F.text == 'Інформація по даті')
async def ask_for_link(message: Message, state: FSMContext):
    await message.answer('Надішліть мені посилання на Google Таблицю або .csv файл, і я виведу інформацію')
    await state.set_state(TableState.waiting_for_link)


# 3. Ловимо правильне посилання
@router.message(TableState.waiting_for_link, F.text.contains('docs.google.com/spreadsheets') | F.text.endswith('.csv'))
async def handle_table_url(message: Message, state: FSMContext):
    await message.answer('Посилання прийнято! Формат підходить, починаю аналіз даних...')

    # Зберігаємо посилання в пам'ять FSM
    await state.update_data(saved_url=message.text)

    await message.answer('Тепер введіть дату (наприклад: 2026-05-24, 2026.05.24 або просто 20260524):')
    await state.set_state(TableState.waiting_for_date)


# 4. Ловимо неправильне посилання (починається з http, але формат не той)
@router.message(TableState.waiting_for_link, F.text.startswith('http'))
async def handle_url(message: Message):
    await message.answer('Надішліть коректне посилання для аналізу')


# 5. Ловимо ДАТУ та викликаємо Pandas
@router.message(TableState.waiting_for_date)
async def handle_date(message: Message, state: FSMContext):
    raw_date = message.text.strip()

    # Авто-форматування дати
    if len(raw_date) == 8 and raw_date.isdigit():
        user_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    else:
        user_date = raw_date.replace('.', '-').replace('/', '-')

    await message.answer(f'Дату {user_date} прийнято! Зчитую таблицю...')

    user_data = await state.get_data()
    url = user_data.get('saved_url')

    # Викликаємо функцію Pandas
    df = read_table_from_link(url)

    # 6. Перевіряємо результат та автоматично аналізуємо будь-яку таблицю
    if df is not None:
        try:
            # Очищаємо назви колонок від випадкових пробілів
            df.columns = df.columns.str.strip()

            # 🔎 АВТОПОШУК КОЛОНКИ З ДАТОЮ
            date_keywords = ['date', 'дата', 'created', 'створено', 'время', 'time']
            date_col_real_name = None

            for keyword in date_keywords:
                for real_name in df.columns:
                    if keyword in real_name.lower():
                        date_col_real_name = real_name
                        break
                if date_col_real_name:
                    break

            if not date_col_real_name:
                await message.answer("❌ Не вдалося автоматично знайти колонку з датою у вашій таблиці.\n"
                                     "Перевірте, щоб у назві стовпця було слово 'Дата' або 'Date'.")
                await state.clear()
                return

            # 🔎 АВТОПОШУК ВСІХ КОЛОНОК ДЛЯ АНАЛІТИКИ
            category_keywords = ['utm_source', 'source', 'джерело', 'stage', 'статус', 'курс', 'тип', 'traf_src']
            analyzed_columns = []

            # Шукаємо ВСІ колонки, які підходять під наші ключові слова
            for real_name in df.columns:
                for keyword in category_keywords:
                    if keyword in real_name.lower() and real_name != date_col_real_name:
                        if real_name not in analyzed_columns:
                            analyzed_columns.append(real_name)

            # 🛠️ ФІЛЬТРАЦІЯ ТА ФОРМУВАННЯ ЗВІТУ (HTML)
            df[date_col_real_name] = pd.to_datetime(df[date_col_real_name], dayfirst=True, errors='coerce')
            target_date = pd.to_datetime(user_date, dayfirst=True, errors='coerce')

            if pd.isna(target_date):
                await message.answer("❌ Некоректний формат дати. Спробуйте: 2025-09-25 або 25.09.2025")
                await state.clear()
                return

            # Фільтруємо строки по вибраній даті
            df_filtered = df[df[date_col_real_name].dt.date == target_date.date()]

            if df_filtered.empty:
                # 🔄 Дані не знайшли, але стан НЕ скидаємо, просимо ввести дату знову!
                await message.answer(f"📭 На дату <b>{user_date}</b> записів у таблиці не знайдено.\n\n"
                                     f"<b>Будь ласка, введіть іншу дату</b> (або натисніть кнопку в меню, щоб почати спочатку):",
                                     parse_mode="HTML")
                return
            else:
                total_rows = len(df_filtered)

                # Головна шапка звіту
                report = f"📊 <b>Універсальний звіт за:</b> <code>{target_date.strftime('%d.%m.%Y')}</code>\n"
                report += f"🔑 Знайдено колонку дат: <code>{date_col_real_name}</code>\n"
                report += f"📈 <b>Всього записів (рядків):</b> <code>{total_rows}</code>\n"
                report += "_______________________\n\n"

                has_any_data = False

                # Проходимо циклом по ВСІХ знайдених аналітичних колонках
                for cat_col in analyzed_columns:
                    counts = df_filtered[cat_col].value_counts(dropna=False)

                    valid_counts = df_filtered[cat_col].dropna()
                    if valid_counts.empty:
                        continue

                    has_any_data = True
                    report += f"📌 <b>Розподіл за <code>{cat_col}</code>:</b>\n"

                    for name, count in counts.items():
                        if pd.isna(name) or str(name).strip() == "":
                            label = "Не вказано"
                        else:
                            label = str(name).replace('<', '&lt;').replace('>', '&gt;')

                        report += f"🔹 <b>{label}</b>: <code>{count}</code> шт.\n"
                    report += "_______________________\n\n"

                if not has_any_data and len(df.columns) > 1:
                    backup_col = df.columns[1]
                    report += f"📌 <b>Розподіл за дефолтною колонкою <code>{backup_col}</code>:</b>\n"
                    counts = df_filtered[backup_col].value_counts()
                    for name, count in counts.items():
                        label = str(name).replace('<', '&lt;').replace('>', '&gt;') if pd.notna(name) and str(
                            name).strip() != "" else "Не вказано"
                        report += f"🔹 <b>{label}</b>: <code>{count}</code> шт.\n"

                # Відправляємо повний звіт
                await message.answer(report, parse_mode="HTML")

                # Скидаємо стан FSM ТІЛЬКИ коли звіт успішно надіслано
                await state.clear()

        except Exception as e:
            await message.answer(f"❌ Виникла помилка під час автоматичного аналізу: {str(e)}")
            await state.clear()  # Скидаємо у разі критичної помилки

    else:
        await message.answer('Не вдалося прочитати таблицю. Перевірте, чи відкритий доступ за посиланнями!')
        await state.clear()


# 7. Заглушка на повністю некоректний текст замість посилання
@router.message(TableState.waiting_for_link)
async def handle_wrong_link(message: Message):
    await message.answer('Будь ласка, надішліть коректне посилання на Google Таблицю або .csv файл!')