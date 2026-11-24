import io
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pdfplumber

# --- НАСТРОЙКИ ---
PAGE_URL = "https://sustec.ru/raspisanie-ptk-ul-gagarina-7/"
GROUP_NAME = "ПР-255/б"
OUTPUT_FILE = "schedule.txt"

BELLS_MON = {"1": "09:25", "2": "11:10", "3": "13:15", "4": "15:00"}
BELLS_WEEKDAY = {"1": "08:30", "2": "10:15", "3": "12:30", "4": "14:15", "5": "16:00", "6": "17:45"}
BELLS_SAT = {"1": "08:30", "2": "10:15", "3": "12:10", "4": "13:55", "5": "15:40", "6": "17:25"}

DAYS_SHORT = {
    "ПОНЕДЕЛЬНИК": "ПН",
    "ВТОРНИК": "ВТ",
    "СРЕДА": "СР",
    "ЧЕТВЕРГ": "ЧТ",
    "ПЯТНИЦА": "ПТ",
    "СУББОТА": "СБ",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
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
    # Добавляем случайный параметр ?nocache=..., чтобы обойти кеш WordPress на sustec.ru
    fresh_url = f"{PAGE_URL}?nocache={int(time.time())}"
    resp = requests.get(fresh_url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        if ".pdf" in href.lower():
            print(f"Найдена ссылка: [{text}] -> {href}")
            if "1-2" in text.lower() or "1-2" in href.lower():
                return urljoin(PAGE_URL, href)

    raise RuntimeError("Ссылка на PDF для 1-2 курсов не найдена.")


def parse_schedule(pdf_bytes: bytes) -> str:
    header_line = "РАСПИСАНИЕ"
    day_key = ""
    lessons = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if pdf.pages:
            first_text = pdf.pages[0].extract_text() or ""
            for line in first_text.splitlines():
                if "РАСПИСАНИЕ" in line.upper():
                    header_line, day_key = format_header(clean_text(line))
                    break

        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for r_idx, row in enumerate(table):
                    if not row:
                        continue
                    for c_idx, cell in enumerate(row):
                        if cell and GROUP_NAME.lower() in cell.lower():
                            for sub_row in table[r_idx + 1:]:
                                if not sub_row or len(sub_row) <= c_idx:
                                    break
                                pair_num = clean_text(sub_row[0])
                                if not pair_num.isdigit():
                                    break
                                subject = clean_subject(clean_text(sub_row[c_idx]))
                                room = ""
                                for next_cell in sub_row[c_idx + 1 : c_idx + 4]:
                                    val = clean_text(next_cell)
                                    if val:
                                        room = val
                                        break
                                if subject:
                                    lessons.append((pair_num, subject, room))
                            break
                    if lessons:
                        break
                if lessons:
                    break
            if lessons:
                break

    if day_key == "ПОНЕДЕЛЬНИК":
        bells = BELLS_MON
    elif day_key == "СУББОТА":
        bells = BELLS_SAT
    else:
        bells = BELLS_WEEKDAY

    lines = [f"[b][c=#C4B5FD]{header_line}[/c][/b]"]

    if day_key == "ПОНЕДЕЛЬНИК":
        lines.append("[b][c=#A78BFA]•[/c][/b] [c=#94A3B8]08:30[/c] [c=#F8FAFC]Классный час[/c]")

    if not lessons:
        lines.append("[c=#94A3B8]Пар нет[/c]")
    else:
        for num, subj, room in lessons:
            time_str = bells.get(num, "")
            room_str = f"  [c=#67E8F9]{room}[/c]" if room else ""
            lines.append(f"[b][c=#A78BFA]{num}[/c][/b] [c=#94A3B8]{time_str}[/c]{room_str}")
            lines.append(f"[c=#F8FAFC]{subj}[/c]")

    return "\n".join(lines)


def main():
    pdf_url = find_pdf_url()
    print(f"Скачиваю PDF: {pdf_url}")
    pdf_resp = requests.get(f"{pdf_url}?nocache={int(time.time())}", headers=HEADERS, timeout=30)
    pdf_resp.raise_for_status()

    result = parse_schedule(pdf_resp.content)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result + "\n")

    print("Результат:\n" + result)


if __name__ == "__main__":
    main()
                                    
