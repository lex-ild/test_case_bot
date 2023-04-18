import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message
from aiogram.utils import executor

from utils import get_weather, convert_currency, get_random_animal_pic

# сюда отправляем опросы
POLLS_CHAT_ID = '723472009'

# Инициализация бота и хранилища состояний
API_TOKEN = os.getenv('TOKEN')
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
# Для хранения состояний в памяти используем MemoryStorage
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class WeatherState(StatesGroup):
    get_city_name = State()
    get_text = State()


class CurrencyConvertState(StatesGroup):
    source = State()
    target = State()
    amount = State()


class PollStates(StatesGroup):
    create_poll = State()
    get_options = State()
    target = State()
    amount = State()


# Обработка команды /start
@dp.message_handler(Command('start'))
async def cmd_start(message: types.Message):
    # Отправляем приветственное сообщение и предлагаем выбрать функцию
    await message.reply("Привет! Я бот, который может выполнить следующие функции:\n"
                        "/weather - Узнать текущую погоду в городе\n"
                        "/convert - Конвертировать валюты\n"
                        "/cute_animal - Получить случайную картинку с милым животным\n"
                        "/poll - Создать опрос")


# Обработка команды /weather
@dp.message_handler(Command('weather'))
async def cmd_weather(message: types.Message):
    # Отправляем сообщение с просьбой ввести название города
    await bot.send_message(chat_id=message.chat.id, text='Введите название города:')
    await WeatherState.get_city_name.set()


# Обработка введенного названия города для определения погоды
@dp.message_handler(state=WeatherState.get_city_name)
async def process_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['city'] = message.text

        # Получаем текущую погоду с помощью API OpenWeatherMap
        city = data['city']
        weather = await get_weather(city)

        # Если удалось получить погоду, отправляем ее пользователю
        if weather is None:
            await bot.send_message(chat_id=message.chat.id, text="Не удалось получить погоду для указанного города.")
        elif weather:
            await bot.send_message(chat_id=message.chat.id, text=f'В г. {city} сейчас {weather} градусов')

    # Возвращаемся в состояние /start
    await state.finish()


# Хэндлер для команды /convert
@dp.message_handler(commands='convert')
async def on_currency_convert(message: types.Message):
    await message.reply("Введите исходную валюту, например, USD:")
    await CurrencyConvertState.source.set()


# Хэндлер для обработки ввода исходной валюты
@dp.message_handler(state=CurrencyConvertState.source)
async def on_currency_convert_source(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['source_currency'] = message.text
    await message.reply("Введите целевую валюту. Например, EUR:")
    await CurrencyConvertState.target.set()


# Хэндлер для обработки ввода целевой валюты и выполнения конвертации валюты
@dp.message_handler(state=CurrencyConvertState.target)
async def on_currency_convert_target(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['target_currency'] = message.text
    await message.reply("Введите сумму для конвертации:")
    await CurrencyConvertState.amount.set()


# Хэндлер для обработки ввода суммы для конвертации и отправки результата конвертации
@dp.message_handler(state=CurrencyConvertState.amount)
async def on_currency_convert_amount(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            data['amount'] = float(message.text)
            source_currency = data['source_currency'].upper()
            target_currency = data['target_currency'].upper()
            amount = data['amount']
            result = await convert_currency(source_currency, target_currency, amount)
            if result is None:
                await message.reply('Что-то пошло не так, попробуйте позже')
            elif result == 'Валюта не найдена':
                await message.reply(result)
            else:
                await message.reply(
                    f"Результат конвертации:\n{round(amount, 2)} {target_currency} = {round(result, 2)} {source_currency}",
                    reply=False)
            await state.finish()
        except Exception as e:
            await message.reply('Нужно ввести число')


@dp.message_handler(commands='cute_animal')
async def send_random_animal_pic(message: Message):
    pic_url = await get_random_animal_pic()
    if pic_url:
        # Отправляем фото с подписью
        await message.reply_photo(photo=pic_url, caption='Милые животные!')
    else:
        # Если не удалось получить ссылку на фото, отправляем сообщение об ошибке
        await message.reply('Не удалось получить фото.')


@dp.message_handler(commands='poll')
async def create_poll_command(message: types.Message):
    await PollStates.create_poll.set()

    # Отправляем сообщение с текстом инструкции
    await message.reply("Введите вопрос опроса:")


@dp.message_handler(state=PollStates.create_poll)
async def process_poll_question(message: types.Message, state: FSMContext):
    # Получаем вопрос опроса из сообщения
    question = message.text

    # Сохраняем вопрос в состояние FSMContext
    await state.update_data(question=question)
    await PollStates.get_options.set()
    # Переходим к следующему шагу - вводу вариантов ответов
    await message.reply("Введите варианты ответов, каждый в новой строке.")


@dp.message_handler(state=PollStates.get_options)
async def process_poll_answers(message: types.Message, state: FSMContext):
    # Получаем варианты ответов из сообщения
    answers = message.text.split('\n')

    # Сохраняем варианты ответов в состояние FSMContext
    await state.update_data(answers=answers)

    # Получаем данные из состояния FSMContext
    data = await state.get_data()

    # Отправляем опрос в групповой чат. Можно получать id чата также при вводе пользователя
    await bot.send_poll(POLLS_CHAT_ID, question=data['question'], options=data['answers'], is_anonymous=True)

    # Сбрасываем состояние FSMContext
    await state.finish()

    # Отправляем сообщение с информацией о созданном опросе
    await message.reply("Опрос успешно создан!")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

