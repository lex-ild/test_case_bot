import json
import os

import aiohttp


API_KEY = os.getenv('WEATHER_TOKEN')


async def get_weather(city):
    async with aiohttp.ClientSession() as session:
        # Формируем URL для запроса
        url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}'

        async with session.get(url) as response:
            if response.status == 200:
                response_json = await response.read()
                data = json.loads(response_json)
                temp = data['main']['temp']
                # api отдаёт температуру в кельвинах
                celcius = temp - 273.15
                return round(celcius)
            else:
                return None


async def convert_currency(source, target, amount):
    async with aiohttp.ClientSession() as session:
        url = f"https://www.cbr-xml-daily.ru/daily_json.js"
        async with session.get(url) as response:
            if response.status == 200:
                response_json = await response.read()
                data = json.loads(response_json)

                # в api цб всё сравнивается с рублём, поэтому можно сразу брать целевое значение
                if source == 'RUB':
                    target_rate = data['Valute'][target]['Value']
                    converted_amount = amount * target_rate
                elif target == 'RUB':
                    source_rate = data['Valute'][source]['Value']
                    converted_amount = amount * source_rate
                else:
                    source_rate = data['Valute'][source]['Value']
                    target_rate = data['Valute'][target]['Value']
                    converted_amount = (amount / source_rate) * target_rate
                return round(converted_amount, 2)
            else:
                return None


async def get_random_animal_pic():
    # забираем рандомную собаку
    async with aiohttp.ClientSession() as session:
        url = 'https://random.dog/woof.json'
        async with session.get(url) as response:
            if response.status == 200:
                response_json = await response.read()
                data = json.loads(response_json)
                return data['url']
            else:
                return None

