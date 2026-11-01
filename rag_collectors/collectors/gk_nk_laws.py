import asyncio
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml
from playwright.async_api import async_playwright

from collectors.base import BaseCollector
from config.settings import CNTD_MAX_DOCS, CNTD_THEME_URL, LEGAL_DIR, USER_AGENT

EXCLUDE_KEYWORDS = [
    "земельн", "жилищн", "квартир", "участок", "здание", "помещение",
    "лесной", "недра", "рыболовств", "медицинск", "детск", "школ", "гидротехническ"
]

INCLUDE_KEYWORDS = [
    "транспортн", "движим", "автомобил", "средств", "прокат", "лизинг",
    "выкуп", "аренд", "налог", "финансов", "имуществен", "рассрочк",
    "ндс", "налог на прибыль", "амортизац", "утильсбор", "осаго"
]

HIGH_PRIORITY_KEYWORDS = [
    "лизинг", "финансов аренд", "аренда транспортн", "прокат", "выкуп", "раскат"
]

MEDIUM_PRIORITY_KEYWORDS = [
    "залог", "неустойк", "ответственност", "убытк", "ндс", "налог на прибыль", "транспортн налог"
]


def determine_priority(title: str, text: str) -> str:
    """Определение приоритета документа для RAG в компании по раскату авто"""
    combined = (title + " " + text[:500]).lower()
    if any(k in combined for k in HIGH_PRIORITY_KEYWORDS):
        return "high"
    if any(k in combined for k in MEDIUM_PRIORITY_KEYWORDS):
        return "medium"
    return "standard"


def should_download(title: str) -> bool:
    """Фильтрация нормативных актов по релевантности автобизнесу и лизингу"""
    title_lower = title.lower()
    has_exclude = any(exc in title_lower for exc in EXCLUDE_KEYWORDS)
    has_include = any(inc in title_lower for inc in INCLUDE_KEYWORDS)

    if has_exclude:
        return has_include
    return True


class LawsCollector(BaseCollector):
    """
    Коллектор нормативно-правовой базы (ГК РФ, НК РФ, законы о лизинге и транспорте).
    Регламент запуска: Раз в 3 месяца.
    Формат: .md файлы с YAML frontmatter.
    """

    def __init__(self):
        super().__init__("laws_gk_nk")
        self.output_dir = LEGAL_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def collect(self) -> Dict[str, Any]:
        self.logger.info(f"Запуск сбора законов с {CNTD_THEME_URL}")
        saved_count = 0
        skipped_count = 0

        async with async_playwright() as p:
            # Настройки для стабильной работы на Linux-сервере (Headless, без песочницы)
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process"
                ]
            )

            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 1024}
            )

            # Блокируем тяжелые ресурсы (картинки, шрифты, метрики) для ускорения в 5 раз
            page = await context.new_page()
            await page.route(
                "**/*",
                lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] or any(
                    x in route.request.url for x in ["yandex", "google-analytics", "metrika", "mc.yandex.ru"]
                ) else route.continue_()
            )

            try:
                self.logger.info(f"Переход на каталог документов: {CNTD_THEME_URL}")
                # Используем domcontentloaded вместо load для избежания таймаутов на сервере
                await page.goto(CNTD_THEME_URL, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_selector(".document-list, body", timeout=20000)

                # Прокручиваем страницу пачками
                last_count = 0
                retries = 0
                max_scroll_retries = 4

                self.logger.info("Прокрутка каталога для сбора списка актов...")
                while True:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    await asyncio.sleep(1.5)
                    current_items = await page.locator("li.document-list_i").count()

                    if current_items >= CNTD_MAX_DOCS:
                        self.logger.info(f"Достигнут лимит выборки ({CNTD_MAX_DOCS} актов).")
                        break

                    if current_items == last_count:
                        retries += 1
                        if retries >= max_scroll_retries:
                            self.logger.info("Конец каталога достигнут.")
                            break
                    else:
                        retries = 0
                        last_count = current_items

                document_elements = await page.locator("li.document-list_i").all()
                self.logger.info(f"Найдено документов в каталоге: {len(document_elements)}")

                for item in document_elements:
                    try:
                        link_elem = item.locator("a.document-list_i_lk").first
                        href = await link_elem.get_attribute("href") or ""
                        title_elem = item.locator("div.document-list_i_t").first
                        title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else "Без названия"

                        details_elem = item.locator("div.__color_grey").first
                        details = (await details_elem.inner_text()).strip() if await details_elem.count() > 0 else "Реквизиты отсутствуют"

                        if not should_download(title):
                            skipped_count += 1
                            continue

                        doc_id = href.split("/")[-1] if "/" in href else str(int(time.time() * 1000))
                        doc_url = f"https://docs.cntd.ru{href}" if href.startswith("/") else href

                        # Скачиваем полный текст документа
                        doc_page = await context.new_page()
                        doc_page.set_default_timeout(25000)
                        try:
                            await doc_page.goto(doc_url, wait_until="domcontentloaded")
                            await doc_page.wait_for_selector(".text, .document-content, body", timeout=10000)
                            full_text = await doc_page.locator("body").inner_text()

                            # Очистка от служебного мусора
                            cleaned_lines = [
                                line.strip() for line in full_text.split("\n")
                                if line.strip() and "© АО «Кодекс»" not in line and "Личный кабинет" not in line
                            ]
                            document_body = "\n".join(cleaned_lines)
                        except Exception as e:
                            self.logger.warning(f"Не удалось извлечь текст {doc_url}: {e}")
                            document_body = f"Не удалось извлечь полный текст. Исходная ссылка: {doc_url}"
                        finally:
                            await doc_page.close()

                        priority = determine_priority(title, document_body)

                        # Формируем метаданные YAML точно по утвержденной структуре RAG
                        metadata = {
                            "source_site": "docs.cntd.ru",
                            "category": "Нормативная база (ГК РФ / НК РФ)",
                            "original_url": doc_url,
                            "title": title,
                            "details": details,
                            "priority_level": priority,
                            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        # Сохраняем в формате .md с YAML frontmatter
                        filename = f"doc_{doc_id}.md"
                        filepath = self.output_dir / filename
                        frontmatter = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
                        file_content = f"---\n{frontmatter}---\n\n# {title}\n\n**Реквизиты:** {details}\n\n---\n\n{document_body}"

                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(file_content)

                        saved_count += 1
                        if saved_count % 20 == 0:
                            self.logger.info(f"Сохранено нормативных актов: {saved_count}...")

                    except Exception as item_err:
                        self.logger.warning(f"Ошибка при обработке элемента: {item_err}")
                        continue

            finally:
                await browser.close()

        return {
            "items_collected": saved_count,
            "items_skipped": skipped_count,
            "output_directory": str(self.output_dir)
        }
