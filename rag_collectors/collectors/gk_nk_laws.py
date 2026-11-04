import asyncio
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Set

from playwright.async_api import async_playwright

from collectors.base import BaseCollector
from config.settings import (
    CNTD_CIVICS_THEMES,
    CNTD_MAX_DOCS,
    CNTD_TAX_THEMES,
    LEGAL_DIR,
    LEGAL_JSONL_FILE,
    LOGS_DIR,
    USER_AGENT,
)

EXCLUDE_KEYWORDS = [
    "земельн", "жилищн", "квартир", "участок", "здание", "помещение",
    "лесной", "недра", "рыболовств", "медицинск", "детск", "школ", "гидротехническ"
]

INCLUDE_KEYWORDS = [
    "транспортн", "движим", "автомобил", "средств", "прокат", "лизинг",
    "выкуп", "аренд", "налог", "финансов", "имуществен", "рассрочк",
    "ндс", "налог на прибыль", "амортизац", "утильсбор", "осаго", "банкрот"
]

HIGH_PRIORITY_KEYWORDS = [
    "лизинг", "финансов аренд", "аренда транспортн", "прокат", "выкуп", "раскат", "транспортн налог"
]

MEDIUM_PRIORITY_KEYWORDS = [
    "залог", "неустойк", "ответственност", "убытк", "ндс", "налог на прибыль", "страхов"
]


def determine_priority(title: str, text: str) -> str:
    """Определение приоритета документа для RAG в компании по раскату авто"""
    combined = (title + " " + text[:600]).lower()
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


def format_category_slug(name: str) -> str:
    """Формирование читаемого slug для категории"""
    cleaned = re.sub(r'[,.()]+', '', name)
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    return cleaned


class LawsCollector(BaseCollector):
    """
    Коллектор нормативно-правовой базы (ГК РФ и НК РФ) с docs.cntd.ru.
    Сохраняет нормативные акты в единый файл JSONL: data/legal/laws_gk_nk.jsonl
    с префиксами:
      • tax_{id документа}  (НК РФ: НДС, прибыль, транспортный налог, УСН, взносы)
      • civics_{id документа} (ГК РФ: собственность, аренда, лизинг, страхование, банкротство)
    """

    def __init__(self):
        super().__init__("laws_gk_nk")
        self.output_jsonl = LEGAL_JSONL_FILE
        self.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = LOGS_DIR / "laws_collector_detailed.log"

    def _load_existing_ids(self) -> Set[str]:
        existing_ids = set()
        if self.output_jsonl.exists():
            try:
                with open(self.output_jsonl, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                doc = json.loads(line)
                                if "parent_id" in doc:
                                    existing_ids.add(doc["parent_id"])
                            except Exception:
                                continue
            except Exception as e:
                self.logger.warning(f"Ошибка чтения существующего JSONL: {e}")
        return existing_ids

    async def collect(self) -> Dict[str, Any]:
        t0 = time.time()
        self.logger.info("=" * 70)
        self.logger.info("🚀 ЗАПУСК СБОРА НОРМАТИВНОЙ БАЗЫ ГК РФ / НК РФ (docs.cntd.ru)")
        self.logger.info(f"Целевой файл: {self.output_jsonl}")
        self.logger.info("=" * 70)

        existing_ids = self._load_existing_ids()
        self.logger.info(f"Уже в базе JSONL документов: {len(existing_ids)}")

        # Формируем список всех тем с метаданными раздела
        themes_to_crawl = []
        for theme_name, theme_url in CNTD_TAX_THEMES.items():
            themes_to_crawl.append({
                "theme_name": theme_name,
                "url": theme_url,
                "section": "НК РФ",
                "id_prefix": "tax",
                "category": format_category_slug(theme_name)
            })

        for theme_name, theme_url in CNTD_CIVICS_THEMES.items():
            themes_to_crawl.append({
                "theme_name": theme_name,
                "url": theme_url,
                "section": "ГК РФ",
                "id_prefix": "civics",
                "category": format_category_slug(theme_name)
            })

        saved_count = 0
        skipped_count = 0

        async with async_playwright() as p:
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

            # Открываем JSONL файл для дозаписи
            jsonl_fp = open(self.output_jsonl, "a", encoding="utf-8")

            try:
                for t_idx, theme_meta in enumerate(themes_to_crawl, 1):
                    theme_title = theme_meta["theme_name"]
                    theme_url = theme_meta["url"]
                    section = theme_meta["section"]
                    prefix = theme_meta["id_prefix"]
                    category = theme_meta["category"]

                    self.logger.info(f"\n[{t_idx}/{len(themes_to_crawl)}] Раздел: {section} | Тема: {theme_title}")
                    self.logger.info(f"URL: {theme_url}")

                    page = await context.new_page()
                    # Блокировка тяжелых трекеров и картинок для ускорения
                    await page.route(
                        "**/*",
                        lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] or any(
                            x in route.request.url for x in ["yandex", "google-analytics", "metrika", "mc.yandex.ru"]
                        ) else route.continue_()
                    )

                    try:
                        await page.goto(theme_url, wait_until="domcontentloaded", timeout=45000)
                        await page.wait_for_selector(".document-list, body", timeout=15000)

                        # Прокручиваем для подгрузки списка
                        for _ in range(2):
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                            await asyncio.sleep(1.0)

                        items = await page.locator("li.document-list_i").all()
                        self.logger.info(f"Обнаружено документов в каталоге темы: {len(items)}")

                        for item in items[:CNTD_MAX_DOCS]:
                            try:
                                link_elem = item.locator("a.document-list_i_lk").first
                                href = await link_elem.get_attribute("href") or ""
                                title_elem = item.locator("div.document-list_i_t").first
                                title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else "Без названия"

                                details_elem = item.locator("div.__color_grey").first
                                details = (await details_elem.inner_text()).strip() if await details_elem.count() > 0 else "Реквизиты отсутствуют"

                                raw_id = href.split("/")[-1] if "/" in href else str(int(time.time() * 1000))
                                # Убираем query params если есть
                                raw_id = raw_id.split("?")[0]
                                parent_id = f"{prefix}_{raw_id}"

                                if parent_id in existing_ids:
                                    skipped_count += 1
                                    continue

                                if not should_download(title):
                                    skipped_count += 1
                                    continue

                                doc_url = f"https://docs.cntd.ru{href}" if href.startswith("/") else href

                                # Скачивание тела акта
                                doc_page = await context.new_page()
                                doc_page.set_default_timeout(20000)
                                try:
                                    await doc_page.goto(doc_url, wait_until="domcontentloaded")
                                    await doc_page.wait_for_selector(".text, .document-content, body", timeout=8000)
                                    raw_text = await doc_page.locator("body").inner_text()
                                    cleaned = [
                                        line.strip() for line in raw_text.split("\n")
                                        if line.strip() and "© АО «Кодекс»" not in line and "Личный кабинет" not in line
                                    ]
                                    document_body = "\n".join(cleaned)
                                except Exception as crawl_err:
                                    document_body = f"Фрагмент документа из каталога. {details}. Ссылка: {doc_url}"
                                finally:
                                    await doc_page.close()

                                priority = determine_priority(title, document_body)
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                                # Запись строго по утвержденной структуре в JSONL
                                record = {
                                    "parent_id": parent_id,
                                    "source_site": "docs.cntd.ru",
                                    "section": section,
                                    "category": category,
                                    "original_url": doc_url,
                                    "title": title,
                                    "details": details,
                                    "collected_at": now_str,
                                    "priority_level": priority,
                                    "body": document_body
                                }

                                jsonl_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                                jsonl_fp.flush()

                                existing_ids.add(parent_id)
                                saved_count += 1

                                self.logger.info(f"  + [{parent_id}] {title[:60]}... ({section} / {category})")

                            except Exception as item_err:
                                self.logger.warning(f"Ошибка при разборе документа темы: {item_err}")
                                continue

                    except Exception as theme_err:
                        self.logger.warning(f"Ошибка при обработке темы {theme_title}: {theme_err}")
                    finally:
                        await page.close()

            finally:
                jsonl_fp.close()
                await browser.close()

        duration = round(time.time() - t0, 2)
        self.logger.info("=" * 70)
        self.logger.info(f"✅ СБОР ЗАВЕРШЕН ЗА {duration} СЕК")
        self.logger.info(f"Добавлено новых актов в JSONL: {saved_count}")
        self.logger.info(f"Пропущено (дубли / фильтр):   {skipped_count}")
        self.logger.info(f"Всего документов в JSONL:     {len(existing_ids)}")
        self.logger.info("=" * 70)

        return {
            "items_collected": saved_count,
            "items_skipped": skipped_count,
            "total_in_jsonl": len(existing_ids),
            "output_file": str(self.output_jsonl),
            "duration_sec": duration
        }
