import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
import asyncio
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime, date, timedelta

# === Настройки ===
API_TOKEN = '8024432635:AAFOqVwVzxl85g3pS5mWRubmRTXQUGp0QEk'  # Мой токен
START_DATE = date(2024, 9, 1) 

# === Создание бота и диспетчера ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

schedule_data = {
    "Понедельник": {
        "numerator": ["1. Физическая кульутра Кабинет: Спортзал", "2. МДК 02.02 Кабинет: 309", "3. МДК 01.02 Кабинет: 207", "4. МДК 05.01 Кабинет: 309"],
        "denominator": ["1. УП 01.01 Кабинет: 207/209", "2. МДК 02.02 Кабинет: 309", "3. МДК 01.02 Кабинет: 207", "4. МДК 05.01 Кабинет: 309"]
    },
    "Вторник": {
        "numerator": ["1. Нет", "2. Нет", "3. Иностранный язык Кабинет: 408", "4. МДК 01.02 Кабинет: 207", "5. МДК 01.02 Кабинет: 207"],
        "denominator": ["1. Нет", "2. Нет", "3. Нет", "4. МДК 01.02 Кабинет: 207", "5. МДК 01.02 Кабинет: 207"]
    },
    "Среда": {
        "numerator": ["1. УП 01.01 Кабинет: 207/209", "2. УП 01.01 Кабинет: 207/209", "3. МДК 02.02 Кабинет: 309", "4. Иностранный язык Кабинет: 408"],
        "denominator": ["1. УП 01.01 Кабинет: 207/209", "2. УП 01.01 Кабинет: 207/209", "3. МДК 02.02 Кабинет: 309", "4. Иностранный язык Кабинет: 408"]
    },
    "Четверг": {
        "numerator": ["1. УП 02.01 Кабинет: 207/209", "2. УП 02.01 Кабинет: 207/209", "3. УП 02.01 Кабинет: 207/209", "4. МДК 01.02 Кабинет: 207"],
        "denominator": ["1. Физическая кульутра Кабинет: Спортзал", "2. УП 02.01 Кабинет: 207/209", "3. УП 02.01 Кабинет: 207/209", "4. МДК 01.02 Кабинет: 207"]
    },
    "Пятница": {
        "numerator": ["1. Нет", "2. МДК 01.02 Кабинет: 207", "3. МДК 01.02 Кабинет: 207", "4. МДК 01.02 Кабинет: 207", "5. МДК 01.02 Кабинет: 207"],
        "denominator": ["1. Нет", "2. МДК 01.02 Кабинет: 207", "3. МДК 01.02 Кабинет: 207", "4. МДК 01.02 Кабинет: 207", "5. МДК 01.02 Кабинет: 207"]
    }
}

month_names_ru = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

CALLS_MONDAY = '''📅 Расписание звонков на Понедельник:

📌 Разговоры о важном: 8:00 — 8:25

🕐 1 пара:
8:30 — 9:15
9:20 — 10:05

🕑 2 пара:
10:15 — 11:00
11:05 — 11:50

🕒 3 пара:
12:30 — 13:15
13:20 — 14:05

🕓 4 пара:
14:15 — 15:00
15:05 — 15:50

🕓 5 пара:
16:00 — 16:45
16:50 — 17:35
'''

CALLS_TUE_TO_FRI = '''📅 Расписание звонков на Вторник — Пятницу:

🕐 1 пара:
8:00 — 8:45
8:50 — 9:35

🕑 2 пара:
9:45 — 10:30
10:35 — 11:20

🕒 3 пара:
12:00 — 12:45
12:50 — 13:35

🕓 4 пара:
13:45 — 14:30
14:35 — 15:20

🕓 5 пара:
15:30 — 16:15
16:20 — 17:05
'''

# === Кнопки ===
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Основное расписание")],
    [KeyboardButton(text="Замены")],
    [KeyboardButton(text="Расписание звонков")] 
], resize_keyboard=True)

schedule_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="На всю неделю")],
    [KeyboardButton(text="На завтра (основное)")],
    [KeyboardButton(text="Назад")]
], resize_keyboard=True)

replacements_kb = ReplyKeyboardMarkup(keyboard=[
    # [KeyboardButton(text="На сегодня (замены)")],
    [KeyboardButton(text="На завтра (замены)")],
    [KeyboardButton(text="Назад")]
], resize_keyboard=True)

schedule_calls_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Понедельник")],
    [KeyboardButton(text="Вторник-Пятница")],
    [KeyboardButton(text="Назад")]
], resize_keyboard=True)


# === Функции ===
def get_week_type() -> str:
    today = datetime.now().date()
    weeks_passed = (today - START_DATE).days // 7
    return "denominator" if weeks_passed % 2 == 0 else "numerator"

def get_schedule_text(day: str, week_type: str) -> str:
    if day in schedule_data and week_type in schedule_data[day]:
        lines = [f"📅 {day} ({'Числитель' if week_type == 'numerator' else 'Знаменатель'}):"]
        for lesson in schedule_data[day][week_type]:
            lines.append(f"- {lesson}")
        return "\n".join(lines)
    else:
        return f"❌ Не удалось найти расписание для {day}."


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from datetime import datetime

def get_replacements_with_selenium():
    service = Service(executable_path='./chromedriver.exe')
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://vrnbmtk.obrvrn.ru/students/schedule/")

        # Ждём загрузки хотя бы одного <p>
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )

        soup = BeautifulSoup(driver.page_source, "lxml")
        paragraphs = soup.find_all("p")

        def clean_text(text):
            return re.sub(r'\s+', ' ', text).strip()

        # --- Извлечение даты ---
        raw_text = soup.get_text()
        date_match = re.search(r'занятий на (\d{1,2}) (\w+) (\d{4}) года', raw_text, re.IGNORECASE)
        if date_match:
            day, month_str, year = date_match.groups()
            month_map = {
                "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
                "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12
            }
            try:
                month = month_map[month_str.lower()]
                schedule_date = datetime(int(year), month, int(day))
                formatted_date = f"{schedule_date.day} {month_names_ru[schedule_date.month]}"
                date_header = f"📌 Замены для группы КС-31 на {formatted_date}:"
            except KeyError:
                date_header = "📌 Замены для группы КС-31:"
        else:
            date_header = "📌 Замены для группы КС-31:"

        # --- Поиск замен для КС-31 ---
        replacements = []
        found_group = False
        for p in paragraphs:
            text = clean_text(p.get_text())
            if "КС-31" in text:
                found_group = True
                replacements.append(text)
            elif found_group and text:
                replacements.append(text)
            elif found_group and not text:
                break  # Остановка после пустой строки

        if replacements:
            return f"{date_header}\n\n" + "\n".join(f"- {line}" for line in replacements)
        else:
            return "🔄 Сегодня замен для группы КС-31 нет."
    except Exception as e:
        return f"❌ Ошибка при получении замен: {e}"
    finally:
        driver.quit()



# === Хэндлеры ===
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Выберите что хотите посмотреть:", reply_markup=main_kb)

@dp.message(F.text == "Основное расписание")
async def show_schedule_menu(message: Message):
    await message.answer("Выберите день:", reply_markup=schedule_kb)

@dp.message(F.text == "Замены")
async def show_replacements_menu(message: Message):
    await message.answer("Выберите дату:", reply_markup=replacements_kb)

@dp.message(F.text == "На всю неделю")
async def week_schedule(message: Message):
    week_type = get_week_type()
    full_schedule = []
    full_schedule.append("🗓️ Текущая неделя: " + ("Числитель" if week_type == "numerator" else "Знаменатель"))
    full_schedule.append("")
    for day in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]:
        full_schedule.append(f"📅 {day}:")
        if day in schedule_data and week_type in schedule_data[day]:
            for lesson in schedule_data[day][week_type]:
                full_schedule.append(f"- {lesson}")
        else:
            full_schedule.append("- Нет занятий или ошибка в данных")
        full_schedule.append("")
    await message.answer("\n".join(full_schedule), reply_markup=schedule_kb)

@dp.message(F.text == "На завтра (основное)")
async def tomorrow_schedule(message: Message):
    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    today_index = datetime.now().weekday()

    tomorrow_index = (today_index + 1) % 7
    tomorrow_day = days_of_week[tomorrow_index]

    week_type = get_week_type()
    schedule_text = get_schedule_text(tomorrow_day, week_type)
    await message.answer(schedule_text, reply_markup=schedule_kb)

@dp.message(F.text == "На сегодня (замены)")
async def today_replacements(message: Message):
    replacements = get_replacements_with_selenium()
    await message.answer(replacements, reply_markup=replacements_kb)

@dp.message(F.text == "На завтра (замены)")
async def tomorrow_replacements(message: Message):
    replacements = get_replacements_with_selenium()
    await message.answer(replacements, reply_markup=replacements_kb)

@dp.message(F.text == "Назад")
async def go_back(message: Message):
    await message.answer("Вы вернулись в главное меню.", reply_markup=main_kb)

@dp.message(F.text == "Расписание звонков")
async def show_call_schedule_menu(message: Message):
    await message.answer("Выберите день недели:", reply_markup=schedule_calls_kb)

@dp.message(F.text == "Понедельник")
async def calls_monday(message: Message):
    await message.answer(CALLS_MONDAY, reply_markup=schedule_calls_kb)

@dp.message(F.text == "Вторник-Пятница")
async def calls_tue_to_fri(message: Message):
    await message.answer(CALLS_TUE_TO_FRI, reply_markup=schedule_calls_kb)


# === Запуск ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())