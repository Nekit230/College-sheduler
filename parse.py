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

# Только время начала пары — для 2x2 так намного компактнее
BELLS = {
    "1": "08:30",
    "2": "10:15",
    "3": "12:30",
    "4": "14:15",
    "5": "16:00",
    "6": "17:45",
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


def format_header(raw_header: str) -> str:
    upper = raw_header.upper()
    date_match = re.search(r"\d{1,2}\s+[А-ЯЁ]+", upper)
    date_str = date_match.group(0) if date_match else "РАСПИСАНИЕ"

    day_str = ""
    for full_day, short_day in DAYS_SHORT.items():
        if full_day in upper:
            day_str = f" • {short_day}"
            break

    return f"{date_str}{day_str}"


def clean_subject(text: str) -> str:
    # Убираем фамилию и инициалы преподавателя (например, "Герасимова Н.В.")
    text = re.sub(r"\.?\s+[А-ЯЁ][а-яё\-]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?", "", text)
    # Убираем "(1,2)" если мешает, и лишние точки в конце
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
    lessons = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if pdf.pages:
            first_text = pdf.pages[0].extract_text() or ""
            for line in first_text.splitlines():
                if "РАСПИСАНИЕ" in line.upper():
                    header_line = format_header(clean_text(line))
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
                                # Ищем номер аудитории в ближайших ячейках справа
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

    # Форматирование с BBCode-тегами, которые понимает KWGT
    lines = [f"[b][c=#C4B5FD]{header_line}[/c][/b]"]

    if not lessons:
        lines.append("[c=#94A3B8]Пар нет[/c]")
    else:
        for num, subj, room in lessons:
            time_str = BELLS.get(num, "")
            room_str = f"  [c=#67E8F9]{room}[/c]" if room else ""
            lines.append(f"[b][c=#A78BFA]{num}[/c][/b] [c=#94A3B8]{time_str}[/c]{room_str}")
            lines.append(f"[c=#F8FAFC]{subj}[/c]")

    return "\n".join(lines)


def main():
    pdf_url = find_pdf_url()
    pdf_resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
    pdf_resp.raise_for_status()

    result = parse_schedule(pdf_resp.content)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result + "\n")

    print("Готово:\n" + result)


if __name__ == "__main__":
    main()
    

  
