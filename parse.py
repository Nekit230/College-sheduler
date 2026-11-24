import io
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import pdfplumber

# --- НАСТРОЙКИ ---
PAGE_URL = "https://sustec.ru/raspisanie-ptk-ul-gagarina-7/"
GROUP_NAME = "ПР-255/б"  # Ваша группа (можно поменять на любую другую)
OUTPUT_FILE = "schedule.txt"

BELLS = {
    "1": "08:30–10:05",
    "2": "10:15–11:50",
    "3": "12:30–14:05",
    "4": "14:15–15:50",
    "5": "16:00–17:35",
    "6": "17:45–19:20",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def find_pdf_url() -> str:
    resp = requests.get(PAGE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True).lower()
        if ".pdf" in href.lower() and ("1-2" in text or "1-2" in href.lower()):
            return urljoin(PAGE_URL, href)

    raise RuntimeError("Ссылка на PDF с расписанием для 1-2 курсов не найдена.")


def parse_schedule(pdf_bytes: bytes) -> str:
    header_line = "Расписание"
    lessons = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if pdf.pages:
            first_text = pdf.pages[0].extract_text() or ""
            for line in first_text.splitlines():
                if "РАСПИСАНИЕ" in line.upper():
                    header_line = clean_text(line)
                    break

        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for r_idx, row in enumerate(table):
                    if not row:
                        continue
                    for c_idx, cell in enumerate(row):
                        if cell and GROUP_NAME.lower() in cell.lower():
                            # Нашли заголовок нужной группы — читаем пары ниже
                            for sub_row in table[r_idx + 1:]:
                                if not sub_row or len(sub_row) <= c_idx:
                                    break
                                pair_num = clean_text(sub_row[0])
                                # Если в первом столбце больше нет номера пары — начался блок других групп
                                if not pair_num.isdigit():
                                    break
                                subject = clean_text(sub_row[c_idx])
                                room = (
                                    clean_text(sub_row[c_idx + 1])
                                    if c_idx + 1 < len(sub_row)
                                    else ""
                                )
                                if subject:
                                    lessons.append((pair_num, subject, room))
                            break
                    if lessons:
                        break
                if lessons:
                    break
            if lessons:
                break

    lines = [header_line, f"Группа: {GROUP_NAME}", ""]

    if not lessons:
        lines.append("Пар не найдено или расписание ещё не обновлено.")
    else:
        for num, subj, room in lessons:
            time_str = BELLS.get(num, "")
            room_str = f" | каб. {room}" if room else ""
            lines.append(f"{num}. {time_str}{room_str}")
            lines.append(f"   {subj}")

    return "\n".join(lines)


def main():
    pdf_url = find_pdf_url()
    print(f"Скачиваю: {pdf_url}")
    pdf_resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
    pdf_resp.raise_for_status()

    result = parse_schedule(pdf_resp.content)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(result + "\n")

    print("Готово:\n" + result)


if __name__ == "__main__":
    main()
  
