import io
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pdfplumber

# --- НАСТРОЙКИ ---
PAGE_URL = "https://sustec.ru/raspisanie-ptk-ul-gagarina-7/"
GROUP_NAME = "ПР-255/б"
OUTPUT_FILE = "schedule.txt"

# Звонки: Понедельник
BELLS_MON = {
    "1": "09:25",
    "2": "11:10",
    "3": "13:15",
    "4": "15:00",
}

# Звонки: Вторник – Пятница
BELLS_WEEKDAY = {
    "1": "08:30",
    "2": "10:15",
    "3": "12:30",
    "4": "14:15",
    "5": "16:00",
    "6": "17:45",
}

# Звонки: Суббота
BELLS_SAT = {
    "1": "08:30",
    "2": "10:15",
    "3": "12:10",
    "4": "13:55",
    "5": "15:40",
    "6": "17:25",
}

DAYS_SHORT = {
    "ПОНЕДЕЛЬНИК": "ПН",
    "ВТОРНИК": "ВТ",
    "СРЕДА": "СР",
    "ЧЕТВЕРГ": "ЧТ",
    "ПЯТНИЦА": "ПТ",
    "СУББОТА": "СБ",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def format_header(raw_header: str) -> tuple[str, str]:
    upper = raw_header.upper()
    date_match = re.search(r"\d{1,2}\s+[А-ЯЁ]+", upper)
    date_str = date_match.group(0) if date_match else "РАСПИСАНИЕ"

    day_key = ""
    day_str = ""
    for full_day, short_day in DAYS_SHORT.items():
        if full_day in upper:
            day_key = full_day
            day_str = f" • {short_day}"
            break

    return f"{date_str}{day_str}", day_key


def clean_subject(text: str) -> str:
    text = re.sub(r"\.?\s+[А-ЯЁ][а-яё\-]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?", "", text)
    text = re.sub(r"\s*\(1,2\)", "", text)
    return text.strip(" .")


def find_pdf_url() -> str:
    resp = requests.get(PAGE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True).lower()
        if ".pdf" in href.lower() and ("1-2" in text or "1-2" in href.lower()):
            return urljoin(PAGE_URL, href)

    raise RuntimeError("Ссылка на PDF для 1-2 курсов не найдена.")


def parse_schedule(pdf_bytes: bytes) -> str:
    header_line = "РАСПИСАНИЕ"
    day_key = ""
    lessons = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if pdf.pages:
            first_text = pdf.
        
