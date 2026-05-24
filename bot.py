from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
import asyncio
import logging
from handlers.start import router as start_router

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


# Без неё диспетчер не знает о существовании твоих кнопок и функций
dp.include_router(start_router)

#Налаштовуємо вивід инфо.в когсоль
async def main():
    logging.basicConfig(level=logging.INFO)
    #Бот починає слухати(зєднуватися) сервер ТГ
    await dp.start_polling(bot)  # Дужки порожні!

#Точка входу
if __name__ == '__main__':
    asyncio.run(main())