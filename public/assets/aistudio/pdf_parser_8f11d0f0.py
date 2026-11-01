import io
import json
import re
import time
import requests
from pypdf import PdfReader

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def clean_extracted_text(text: str) -> str:
    """Очистка судебного текста от лишних переносов строк и пробелов"""
    if not text:
        return ""
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def download_and_extract_pdf(url: str, retries=3) -> str:
    """Скачивание PDF с несколькими попытками при тайм-ауте"""
    for attempt in range(retries):
        try:
            # Увеличиваем таймаут до 35 секунд
            response = requests.get(url, headers=headers, timeout=35)
            if response.status_code == 200:
                pdf_file = io.BytesIO(response.content)
                reader = PdfReader(pdf_file)

                full_text = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text.append(page_text)

                extracted = "\n\n".join(full_text)
                return clean_extracted_text(extracted)
            else:
                print(f"⚠️ Ошибка HTTP {response.status_code}, попытка {attempt + 1} из {retries}")
        except requests.exceptions.Timeout:
            print(f"⏳ Тайм-аут соединения (попытка {attempt + 1}/{retries}). Повторяем...")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Ошибка сети (попытка {attempt + 1}/{retries}): {e}")
            time.sleep(2)
    return ""


def main():
    input_filename = "vsrf_court_docs.json"
    output_filename = "vsrf_court_docs_rag.json"

    try:
        with open(input_filename, "r", encoding="utf-8") as f:
            input_documents = json.load(f)
    except FileNotFoundError:
        print(f"❌ Файл {input_filename} не найден!")
        return

    rag_documents = []
    print(f"🚀 Найдено документов для обработки: {len(input_documents)}\n" + "=" * 50)

    for idx, item in enumerate(input_documents, 1):
        title = item.get("title", "Без названия")
        url = item.get("url", "")

        if not url or not url.lower().endswith(".pdf"):
            print(f"[{idx}/{len(input_documents)}] ⏭️ Пропускаем не-PDF: {title[:50]}")
            continue

        print(f"[{idx}/{len(input_documents)}] 📥 Загружаем: {title[:60]}...")
        text_content = download_and_extract_pdf(url)

        if text_content:
            doc_entry = {
                "page_content": f"Заголовок: {title}\nТекст документа:\n{text_content}",
                "metadata": {
                    "title": title,
                    "url": url,
                    "source": "vsrf_pdf",
                    "doc_type": "court_decision",
                    "char_length": len(text_content),
                    "is_full_text": True
                }
            }
            rag_documents.append(doc_entry)
            print(f"   [+] Успешно извлечено ({len(text_content)} символов)")
        else:
            print("   [-] Не удалось скачать/прочитать файл после нескольких попыток.")

        # Небольшая вежливая пауза между запросами, чтобы не триггерить защиту от DDoS
        time.sleep(1)
        print("-" * 60)

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(rag_documents, f, ensure_ascii=False, indent=4)

    print(f"\n[SUCCESS] Обработка завершена! Сохранено документов для RAG: {len(rag_documents)}")
    print(f"💾 Итоговый файл сохранен: {output_filename}")


if __name__ == "__main__":
    main()