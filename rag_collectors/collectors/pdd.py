import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

from collectors.base import BaseCollector
from config.settings import (
    HTTP_TIMEOUT,
    LOGS_DIR,
    PDD_DIR,
    PDD_PDF_FILE,
    PDD_PDF_URL,
    PDD_RULES_FILE,
    USER_AGENT,
)


class PDDCollector(BaseCollector):
    """
    Коллектор Правил дорожного движения РФ (ПДД РФ) в формате PDF с официального портала ГИБДД РФ.
    URL: https://гибдд.рф/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf
    (punycode: https://xn--b1aew.xn--p1ai/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf)

    Парсит официальный документ, производит абзацный чанкинг (по пунктам 1.1-26.x,
    обязанностям водителя, знакам и допуску ТС к эксплуатации)
    и сохраняет структурированный JSON в data/pdd/pdd_rules_rag.json.
    """

    def __init__(self):
        super().__init__("pdd_rules")
        self.output_pdf = PDD_PDF_FILE
        self.output_json = PDD_RULES_FILE
        self.output_dir = PDD_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.download_urls = [
            PDD_PDF_URL,
            "https://гибдд.рф/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf",
            "https://xn--b1aew.xn--p1ai/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf"
        ]

    def _download_pdf(self) -> bool:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8"
        }
        for url in self.download_urls:
            try:
                self.logger.info(f"Попытка скачивания ПДД РФ PDF с: {url}...")
                resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT, stream=True)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(self.output_pdf, "wb") as f:
                        f.write(resp.content)
                    self.logger.info(f"PDF успешно сохранен: {self.output_pdf} ({len(resp.content)} байт)")
                    return True
            except Exception as e:
                self.logger.warning(f"Не удалось скачать с {url}: {e}")
        return False

    def _extract_text_from_pdf(self) -> str:
        if not self.output_pdf.exists():
            return ""
        text = ""
        try:
            import pypdf
            reader = pypdf.PdfReader(str(self.output_pdf))
            self.logger.info(f"Извлечение текста из {len(reader.pages)} страниц PDF...")
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                text += f"\n\n--- СТРАНИЦА {idx + 1} ---\n\n" + page_text
        except Exception as e:
            self.logger.warning(f"Ошибка чтения PDF через pypdf ({e}).")
        return text

    def _chunk_pdd_by_paragraphs(self, full_text: str) -> List[Dict[str, Any]]:
        """Разбиение текста ПДД по смысловым пунктам и абзацам"""
        raw_paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        chunks = []
        current_section = "ПДД РФ"
        sec_num = 1

        for p_idx, para in enumerate(raw_paragraphs):
            # Проверка заголовка раздела
            m_sec = re.match(r'^(\d+)\.\s+(.+)$', para)
            if m_sec and len(para) < 120:
                sec_num = int(m_sec.group(1))
                current_section = para
                continue

            # Выявление номера пункта (например, 1.2, 2.1.1, 8.4)
            m_clause = re.search(r'\b(\d+\.\d+(?:\.\d+)?)\b', para)
            clause_num = m_clause.group(1) if m_clause else f"п.{sec_num}.{p_idx}"

            if len(para) >= 40:
                chunks.append({
                    "section_number": sec_num,
                    "section_title": current_section,
                    "clause_number": clause_num,
                    "paragraph_text": para,
                    "topic": f"{current_section} ({clause_num})"
                })
        return chunks

    async def collect(self) -> Dict[str, Any]:
        t0 = time.time()
        self.logger.info("=" * 70)
        self.logger.info("🚀 ЗАПУСК СБОРА И ПАРСИНГА ПДД РФ (ГИБДД РФ PDF)")
        self.logger.info("=" * 70)

        download_success = self._download_pdf()
        extracted_text = self._extract_text_from_pdf() if download_success else ""

        records: List[Dict[str, Any]] = []
        if extracted_text and len(extracted_text) > 500:
            records = self._chunk_pdd_by_paragraphs(extracted_text)
            self.logger.info(f"Сформировано абзацев из скачанного PDF: {len(records)}")

        # Если сеть недоступна или PDF не парсится, используем существующую эталонную базу
        if not records:
            if self.output_json.exists():
                with open(self.output_json, "r", encoding="utf-8") as f:
                    records = json.load(f)
                self.logger.info(f"Использована встроенная эталонная база ПДД: {len(records)} пунктов.")
            else:
                self.logger.warning("База ПДД пуста, запись минимального набора правил...")
                records = [{
                    "section_number": 2,
                    "section_title": "2. Общие обязанности водителей",
                    "clause_number": "2.1.1",
                    "paragraph_text": "Водитель обязан иметь при себе водительское удостоверение, регистрационные документы (СТС), полис ОСАГО.",
                    "topic": "Обязанности водителя"
                }]

        # Сохранение итогового файла
        with open(self.output_json, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        duration = round(time.time() - t0, 2)
        self.logger.info(f"✅ ПДД РФ успешно обработаны и сохранены: {self.output_json}")
        self.logger.info(f"Всего смысловых абзацев/пунктов: {len(records)} (за {duration} с)")
        self.logger.info("=" * 70)

        return {
            "items_collected": len(records),
            "output_file": str(self.output_json),
            "pdf_file": str(self.output_pdf) if self.output_pdf.exists() else None,
            "duration_sec": duration
        }
