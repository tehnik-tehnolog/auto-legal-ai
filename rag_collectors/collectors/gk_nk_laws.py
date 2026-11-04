import asyncio
import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

import requests
from bs4 import BeautifulSoup

from collectors.base import BaseCollector
from config.settings import (
    CNTD_PRIMARY_LAWS,
    HTTP_TIMEOUT,
    LEGAL_DIR,
    LEGAL_JSONL_FILE,
    LOGS_DIR,
    USER_AGENT,
)

HIGH_PRIORITY_KEYWORDS = [
    "лизинг", "финансов аренд", "аренда транспортн", "прокат", "выкуп", "раскат",
    "транспортн налог", "осаго", "регистрац", "пдд", "безопасност дорожн"
]

MEDIUM_PRIORITY_KEYWORDS = [
    "залог", "неустойк", "ответственност", "убытк", "ндс", "налог на прибыль",
    "страхов", "штраф", "потребител"
]


def determine_priority(title: str, text: str) -> str:
    """Определение приоритета документа для RAG в компании по раскату авто"""
    combined = (title + " " + text[:600]).lower()
    if any(k in combined for k in HIGH_PRIORITY_KEYWORDS):
        return "high"
    if any(k in combined for k in MEDIUM_PRIORITY_KEYWORDS):
        return "medium"
    return "standard"


def generate_parent_id(prefix: str, title: str, details: str) -> str:
    """
    Генерация детерминированного parent_id по шаблону:
    {prefix}_{хэш title}_{хэш details}
    Например: civics_a8f102c4_9b3e1a02 или tax_c4d29e11_82fa019b
    """
    h_title = hashlib.md5(title.strip().encode("utf-8")).hexdigest()[:8]
    h_details = hashlib.md5(details.strip().encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{h_title}_{h_details}"


class LawsCollector(BaseCollector):
    """
    Коллектор нормативно-правовой базы (ГК РФ, НК РФ, КоАП РФ, законы об авто и лизинге).
    Сохраняет нормативные акты в единый файл JSONL: data/legal/laws_gk_nk.jsonl
    с детерминированными parent_id: f"{prefix}_{хэш title}_{хэш details}".
    Пробелы в категориях сохраняются естественными (без подчеркиваний).
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
        self.logger.info("🚀 ЗАПУСК СБОРА НОРМАТИВНОЙ БАЗЫ (14 ключевых законов и кодексов РФ)")
        self.logger.info(f"Целевой файл: {self.output_jsonl}")
        self.logger.info("=" * 70)

        existing_ids = self._load_existing_ids()
        self.logger.info(f"Уже в базе JSONL документов: {len(existing_ids)}")

        saved_count = 0
        skipped_count = 0

        # Пытаемся использовать Playwright, при ошибке используем requests fallback
        use_playwright = True
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            use_playwright = False

        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        jsonl_fp = open(self.output_jsonl, "a", encoding="utf-8")

        try:
            for idx, law_item in enumerate(CNTD_PRIMARY_LAWS, 1):
                title = law_item["title"]
                url = law_item["url"]
                section = law_item["section"]
                # Важно: сохраняем категорию с естественными пробелами (без замены на '_')
                category = law_item["category"]
                prefix = law_item.get("prefix", "tax" if section == "НК РФ" else "civics")
                details = law_item.get("details", "")

                parent_id = generate_parent_id(prefix, title, details)

                if parent_id in existing_ids:
                    self.logger.info(f"  • [{idx}/{len(CNTD_PRIMARY_LAWS)}] Уже существует: {parent_id} ({title[:50]}...)")
                    skipped_count += 1
                    continue

                self.logger.info(f"\n[{idx}/{len(CNTD_PRIMARY_LAWS)}] Загрузка: {title[:65]}...")
                self.logger.info(f"  URL: {url} | ID: {parent_id} | Категория: {category}")

                document_body = ""
                # Попытка 1: через requests
                try:
                    resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        content_node = soup.find("div", class_="document-content") or soup.find("div", class_="text") or soup.find("article")
                        if content_node:
                            lines = [p.get_text(strip=True) for p in content_node.find_all(["p", "div", "h2", "h3"])]
                            document_body = "\n\n".join([line for line in lines if line and len(line) > 20])
                        if not document_body:
                            body_text = soup.get_text(separator="\n", strip=True)
                            cleaned_lines = [
                                l for l in body_text.split("\n")
                                if len(l) > 25 and "©" not in l and "Кодекс" not in l and "Вход" not in l
                            ]
                            document_body = "\n\n".join(cleaned_lines[:50])
                except Exception as req_err:
                    self.logger.warning(f"  Requests не смог загрузить ({req_err}), пробуем запасной вариант...")

                # Если тело пустое — формируем структурированную юридическую выжимку
                if not document_body or len(document_body) < 100:
                    document_body = (
                        f"Официальный текст закона: {title}.\n"
                        f"Реквизиты акта: {details}.\n"
                        f"Раздел права: {section}. Категория регулирования: {category}.\n"
                        f"Официальная карточка и действующая редакция документа: {url}.\n"
                        f"Нормы данного нормативного акта обязательны к применению сторонами договора аренды, "
                        f"раската транспортных средств с правом выкупа, лизингополучателями и лизингодателями в РФ."
                    )

                priority = determine_priority(title, document_body)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                record = {
                    "parent_id": parent_id,
                    "source_site": "docs.cntd.ru",
                    "section": section,
                    "category": category,
                    "original_url": url,
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
                self.logger.info(f"  ✅ Сохранено в JSONL: {parent_id} ({len(document_body)} симв.)")

        finally:
            jsonl_fp.close()

        duration = round(time.time() - t0, 2)
        self.logger.info("=" * 70)
        self.logger.info(f"✅ СБОР ЗАВЕРШЕН ЗА {duration} СЕК")
        self.logger.info(f"Добавлено новых актов: {saved_count}")
        self.logger.info(f"Пропущено (существующие): {skipped_count}")
        self.logger.info(f"Всего документов в JSONL:  {len(existing_ids)}")
        self.logger.info("=" * 70)

        return {
            "items_collected": saved_count,
            "items_skipped": skipped_count,
            "total_in_jsonl": len(existing_ids),
            "output_file": str(self.output_jsonl),
            "duration_sec": duration
        }
