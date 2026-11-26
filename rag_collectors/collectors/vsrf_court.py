import asyncio
import io
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import requests
    from pypdf import PdfReader
except ImportError:
    requests = None
    PdfReader = None
try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None
import urllib.request

from collectors.base import BaseCollector
from config.settings import COURT_DIR, USER_AGENT, VSRF_KEYWORD, VSRF_URL, VSRF_YEARS


def clean_extracted_text(text: str) -> str:
    """Clean extracted judicial text from line breaks, OCR artifacts, and extra whitespace."""
    if not text:
        return ""
    # Rejoin hyphenated line-break words
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Collapse single newlines into spaces while keeping paragraph breaks
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_case_metadata(title: str) -> Dict[str, str]:
    """Extract case number and ruling date from Supreme Court decision title."""
    case_num = ""
    date_str = ""

    # Match case number such as № 5-КГ23-12-К2 or Дело № А40-...
    num_match = re.search(r"[№N]\s*([0-9А-ЯA-Z\-КГ]+)", title, re.IGNORECASE)
    if num_match:
        case_num = num_match.group(1).strip()

    # Match date in DD.MM.YYYY format
    date_match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", title)
    if date_match:
        date_str = date_match.group(1)

    return {
        "case_number": case_num or "Не указан",
        "doc_date": date_str or "Не указана"
    }


class VSRFCourtCollector(BaseCollector):
    """
    Collector for Supreme Court of the Russian Federation rulings on automotive/leasing disputes.
    Combines vsrf.ru search and streaming PDF extraction into a single pipeline.
    Schedule: Monthly.
    Output format: vsrf_court_docs_rag.json (page_content + metadata).
    """

    def __init__(self):
        super().__init__("vsrf_court")
        self.output_file = COURT_DIR / "vsrf_court_docs_rag.json"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def download_and_extract_pdf(self, url: str, retries: int = 3) -> str:
        """Download PDF into memory and extract plain text."""
        for attempt in range(1, retries + 1):
            try:
                resp = self.session.get(url, timeout=35)
                if resp.status_code == 200:
                    pdf_bytes = io.BytesIO(resp.content)
                    reader = PdfReader(pdf_bytes)

                    pages_text = []
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            pages_text.append(extracted)

                    full_text = "\n\n".join(pages_text)
                    return clean_extracted_text(full_text)
                else:
                    self.logger.warning(f"HTTP {resp.status_code} при загрузке {url} (попытка {attempt})")
            except requests.exceptions.Timeout:
                self.logger.warning(f"Таймаут соединения для {url} (попытка {attempt}/{retries})")
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Сетевая ошибка для {url}: {e}")
                time.sleep(2)
        return ""

    async def collect(self) -> Dict[str, Any]:
        self.logger.info("Поиск судебных актов на портале Верховного Суда РФ...")

        # Load existing documents for incremental updates
        existing_docs: List[Dict[str, Any]] = []
        known_urls = set()

        if self.output_file.exists():
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    existing_docs = json.load(f)
                    known_urls = {doc.get("metadata", {}).get("url") for doc in existing_docs if "metadata" in doc}
                self.logger.info(f"Загружено ранее собранных документов: {len(existing_docs)}")
            except Exception as load_err:
                self.logger.warning(f"Не удалось прочитать существующий файл: {load_err}")

        found_links = []

        async with async_playwright() as p:
            # Always run headless in server/container environments
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()

            try:
                self.logger.info(f"Переход на страницу поиска: {VSRF_URL}")
                await page.goto(VSRF_URL, wait_until="networkidle", timeout=45000)

                # Enter search keyword
                input_selector = "input#documents-form-keyword"
                await page.wait_for_selector(input_selector, timeout=15000)
                await page.click(input_selector)
                await page.fill(input_selector, VSRF_KEYWORD)

                # Apply year checkboxes
                self.logger.info(f"Установка фильтров по годам: {', '.join(VSRF_YEARS)}")
                for year in VSRF_YEARS:
                    checkbox_selector = f"button#checkbox-{year}"
                    try:
                        checkbox = page.locator(checkbox_selector)
                        if await checkbox.count() > 0:
                            is_checked = await checkbox.get_attribute("aria-checked")
                            if is_checked == "false":
                                await checkbox.click()
                                await page.wait_for_timeout(300)
                    except Exception as chk_err:
                        self.logger.debug(f"Чекбокс {year} пропущен: {chk_err}")

                # Submit search form
                submit_btn = "button[type='submit'][form='documents-form']"
                await page.click(submit_btn)
                await page.wait_for_timeout(4000)

                # Paginate / load more results
                max_loads = 15
                loads_count = 0
                while loads_count < max_loads:
                    try:
                        load_more_btn = page.locator("button:has-text('Показать ещё'), button:has-text('Загрузить ещё')").first
                        if await load_more_btn.count() > 0 and await load_more_btn.is_visible():
                            await load_more_btn.click()
                            loads_count += 1
                            await page.wait_for_timeout(2500)
                        else:
                            break
                    except Exception:
                        break

                # Collect all candidate PDF links
                all_links = await page.locator("a[href]").all()
                self.logger.info(f"Найдено ссылок на странице: {len(all_links)}")

                for link in all_links:
                    href = await link.get_attribute("href")
                    title = await link.inner_text()
                    if href and title:
                        clean_title = title.strip().replace("\n", " ")
                        is_document = ("/media-proxy/" in href or href.lower().endswith(".pdf"))
                        is_external = any(ext in href for ext in [
                            "kremlin.ru", "ksrf.ru", "sudrf.ru", "arbitr.ru", "cdep.ru", "rgup.ru", "gov.ru"
                        ])
                        is_service = any(skip in href for skip in ["/lk", "/contacts", "/press-center", "/about/"])

                        if is_document and not is_external and not is_service and len(clean_title) > 10:
                            full_url = f"https://www.vsrf.ru{href}" if href.startswith("/") else href
                            found_links.append({"title": clean_title, "url": full_url})

            finally:
                await browser.close()

        # Deduplicate links by URL
        unique_links = list({item["url"]: item for item in found_links}.values())
        self.logger.info(f"Найдено уникальных актов ВС РФ: {len(unique_links)}")

        # Download and parse PDF contents
        newly_processed = 0
        final_rag_documents = list(existing_docs)

        for idx, item in enumerate(unique_links, 1):
            url = item["url"]
            title = item["title"]

            if url in known_urls:
                continue

            self.logger.info(f"[{idx}/{len(unique_links)}] Скачивание PDF: {title[:65]}...")
            text_content = self.download_and_extract_pdf(url)

            if text_content:
                parsed_meta = extract_case_metadata(title)
                doc_entry = {
                    "page_content": f"Заголовок: {title}\nНомер дела: {parsed_meta['case_number']}\nДата: {parsed_meta['doc_date']}\nТекст постановления:\n{text_content}",
                    "metadata": {
                        "title": title,
                        "case_number": parsed_meta["case_number"],
                        "date": parsed_meta["doc_date"],
                        "url": url,
                        "source": "vsrf.ru",
                        "doc_type": "court_decision",
                        "category": "Судебная практика ВС РФ (автомобили/лизинг)",
                        "char_length": len(text_content),
                        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                final_rag_documents.append(doc_entry)
                known_urls.add(url)
                newly_processed += 1
                self.logger.info(f"   [+] Успешно извлечено {len(text_content)} символов")
            else:
                self.logger.warning(f"   [-] Пропущен документ {url}")

            # Polite request delay
            time.sleep(1.2)

        # Save final RAG JSON file
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(final_rag_documents, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Итоговый файл сохранен: {self.output_file} (всего актов: {len(final_rag_documents)})")

        return {
            "items_collected": len(final_rag_documents),
            "new_items_added": newly_processed,
            "output_file": str(self.output_file)
        }
