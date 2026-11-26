import asyncio
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    requests = None
import urllib.request

from collectors.base import BaseCollector
from config.settings import (
    HTTP_TIMEOUT,
    LOGS_DIR,
    PDD_CHAPTERS_FILE,
    PDD_DIR,
    PDD_PDF_FILE,
    PDD_PDF_URL,
    PDD_RULES_FILE,
    USER_AGENT,
)


class PDDCollector(BaseCollector):
    """
    Collector for official Russian Traffic Rules (PDD RF) PDF from gibdd.ru.
    URL: https://xn--b1aew.xn--p1ai/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf

    Extracts and parses chapters 1-26, vehicle admission rules, and the vehicle fault list
    into structured JSONL (data/pdd/pdd_chapters.jsonl) and RAG JSON (data/pdd/pdd_rules_rag.json).
    """

    def __init__(self):
        super().__init__("pdd_rules")
        self.output_pdf = PDD_PDF_FILE
        self.output_json = PDD_RULES_FILE
        self.output_chapters = PDD_CHAPTERS_FILE
        self.output_dir = PDD_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.download_urls = [
            PDD_PDF_URL,
            "https://гибдд.рф/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf",
            "https://xn--b1aew.xn--p1ai/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf"
        ]

    def _download_pdf(self) -> bool:
        if self.output_pdf.exists() and self.output_pdf.stat().st_size > 1000:
            self.logger.info(f"Локальный PDF уже существует ({self.output_pdf}), используем его.")
            return True
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8"
        }
        for url in self.download_urls:
            try:
                self.logger.info(f"Попытка скачивания ПДД РФ PDF с: {url}...")
                content = None
                timeout = 4
                if requests:
                    resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
                    if resp.status_code == 200:
                        content = resp.content
                else:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=timeout) as response:
                        content = response.read()

                if content and len(content) > 1000:
                    with open(self.output_pdf, "wb") as f:
                        f.write(content)
                    self.logger.info(f"PDF успешно сохранен: {self.output_pdf} ({len(content)} байт)")
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
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text += page_text
        except Exception as e:
            self.logger.warning(f"Ошибка чтения PDF через pypdf ({e}).")
        return text

    @staticmethod
    def clean_pdd_text(text: str) -> str:
        """
        Clean and format PDD RF text:
        - Replace <*> markers with italicized footnote text.
        - Rejoin hyphenated line breaks and collapse single newlines.
        - Bold quoted phrases and italicize clause numbers (e.g. 2.1.1(1), 2.7).
        """
        if not text:
            return ""

        # 1. Process footnotes matching "-------------------------------- <*> Footnote text"
        footnote_pattern = r'--------------------------------\s*<\*>\s*([^\n]+)'
        match_fn = re.search(footnote_pattern, text)
        if match_fn:
            fn_text = match_fn.group(1).strip()
            # Remove footer block from text
            text = re.sub(footnote_pattern, '', text)
            # Replace inline <*> markers with italicized footnote text
            text = text.replace('<*>', f'*{fn_text}*')

        # Strip leftover separator rules
        text = re.sub(r'-{3,}', '', text)

        # 2. Rejoin hyphenated line breaks
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)

        # 3. Collapse single line breaks into spaces while preserving paragraph boundaries
        clean_pattern = r'(?<!\n)\n(?!\n|\s*["\'«„]|\s*[А-ЯЁA-Z]|\s*\d+(?:\.\d+)*\.?)'
        text = re.sub(clean_pattern, ' ', text)

        # 4. Normalize structural breaks to double newlines
        text = re.sub(r'\n+', '\n\n', text)

        # 5. Collapse extra spaces and tabs
        text = re.sub(r'[ \t]+', ' ', text)

        # 6. Bold quoted terms
        text = re.sub(r'"([^"]+)"', r'**"\1"**', text)
        text = re.sub(r'«([^»]+)»', r'**«\1»**', text)

        # 7. Italicize numbered clauses (e.g. 2.1.1(1), 2.7., 12.1)
        item_pattern = r'\b(\d+\.\d+(?:\.\d+)?(?:\(\d+\))?\.?)\b'
        text = re.sub(item_pattern, r'*\1*', text)

        return text.strip()


    def _parse_pdd_chapters(self, full_text: str, test_mode: bool = False) -> List[Dict[str, Any]]:
        """Parse PDD chapters with prior cleaning and Markdown formatting."""
        chapters = []

        # 1. Locate start marker of Chapter 1
        start_pattern = re.compile(
            r'(?:1\.\s+)?Общие\s+положения',
            re.IGNORECASE | re.DOTALL
        )
        match_start = start_pattern.search(full_text)

        if match_start:
            work_text = full_text[match_start.start():]
            self.logger.info("✅ Маркер старта ПДД успешно найден в тексте документа.")
        else:
            self.logger.warning("⚠️ Точный маркер старта не найден, используем весь текст.")
            work_text = full_text

        # --- Apply text normalization and Markdown formatting ---
        work_text = self.clean_pdd_text(work_text)
        # ------------------------------------------------------

        # 2. Locate Appendices boundary to separate core chapters from sign/marking appendices
        app_cut = re.search(r'Приложение\s+1\s+к\s+Правилам\s+дорожного\s+движения', work_text, re.IGNORECASE)
        main_body_text = work_text[:app_cut.start()] if app_cut else work_text

        # 3. Match core chapters 1-26
        chapter_pattern = re.compile(
            r'(?:^|\n)\s*\*?([1-9]|1[0-9]|2[0-6])\.\*?(?![\d])\s+([А-ЯЁ][^\n]+)',
            re.MULTILINE
        )

        matches = list(chapter_pattern.finditer(main_body_text))
        self.logger.info(f"Найдено основных глав ПДД (1-26): {len(matches)}")

        for i, match in enumerate(matches):
            sec_num = int(match.group(1))
            sec_title_raw = re.sub(r'\s+', ' ', match.group(2)).strip()
            sec_title = f"{sec_num}. {sec_title_raw}"

            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(main_body_text)

            body = main_body_text[start_pos:end_pos].strip()

            if body:
                chapters.append({
                    "section_number": sec_num,
                    "chapter_number": f"Глава {sec_num}",
                    "chapter_title": sec_title,
                    "title": f"ПДД РФ: {sec_title}",
                    "body": body
                })
                if test_mode:
                    break

        # 4. Extract post-appendix sections (Vehicle Admission Rules & Fault List)
        rest_text = work_text[app_cut.start():] if app_cut else ""

        m_admit = re.search(r'ОСНОВНЫЕ\s+ПОЛОЖЕНИЯ\s+ПО\s+ДОПУСКУ\s+ТРАНСПОРТНЫХ\s+СРЕДСТВ', rest_text, re.IGNORECASE)
        m_faults = re.search(r'ПЕРЕЧЕНЬ\s+НЕИСПРАВНОСТЕЙ\s+И\s+УСЛОВИЙ', rest_text, re.IGNORECASE)

        if m_admit:
            admit_start = m_admit.start()
            admit_end = m_faults.start() if m_faults else len(rest_text)
            admit_body = rest_text[admit_start:admit_end].strip()

            chapters.append({
                "section_number": 27,
                "chapter_number": "Основные положения",
                "chapter_title": "Основные положения по допуску ТС к эксплуатации",
                "title": "ПДД РФ: Основные положения по допуску ТС к эксплуатации",
                "body": admit_body
            })
            self.logger.info("✅ Добавлен блок: Основные положения по допуску ТС")

        if m_faults:
            faults_start = m_faults.start()
            faults_body = rest_text[faults_start:].strip()

            chapters.append({
                "section_number": 28,
                "chapter_number": "Перечень неисправностей",
                "chapter_title": "Перечень неисправностей и условий, при которых запрещается эксплуатация ТС",
                "title": "ПДД РФ: Перечень неисправностей, запрещающих эксплуатацию ТС",
                "body": faults_body
            })
            self.logger.info("✅ Добавлен блок: Перечень неисправностей ТС")

        self.logger.info(f"Всего сформировано структурированных объектов: {len(chapters)}")
        return chapters

    async def collect(self, test_mode: bool = False) -> Dict[str, Any]:
        t0 = time.time()
        self.logger.info("=" * 70)
        mode_str = "ТЕСТОВЫЙ ПРОГОН НА 1 ГЛАВЕ" if test_mode else "ПОЛНЫЙ СБОР БАЗЫ"
        self.logger.info(f"🚀 ЗАПУСК СБОРА И ПАРСИНГА ПДД РФ ({mode_str})")
        self.logger.info("=" * 70)

        # Ensure PDF exists locally or download it
        if not self.output_pdf.exists():
            self._download_pdf()

        extracted_text = self._extract_text_from_pdf()
        chapters = []

        if extracted_text and len(extracted_text) > 1000:
            chapters = self._parse_pdd_chapters(extracted_text, test_mode=test_mode)
            self.logger.info(f"Сформировано структурированных глав из PDF: {len(chapters)}")

        # Save to data/pdd/pdd_chapters.jsonl
        with open(self.output_chapters, "w", encoding="utf-8") as f_jsonl:
            for ch in chapters:
                rec = {
                    "parent_id": f"pdd_ch{ch['section_number']}",
                    "doc_id": f"pdd_ch{ch['section_number']}",
                    "section_number": ch["section_number"],
                    "chapter_number": ch["chapter_number"],
                    "chapter_title": ch["chapter_title"],
                    "title": ch["title"],
                    "category": "Правила дорожного движения РФ",
                    "original_url": PDD_PDF_URL,
                    "url": f"#doc-pdd_pdd_ch{ch['section_number']}",
                    "local_doc_id": f"pdd_pdd_ch{ch['section_number']}",
                    "priority_level": "high",
                    "body": ch["body"],
                    "full_text": f"# {ch['title']}\n\n{ch['body']}"
                }
                f_jsonl.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # Save legacy RAG JSON output
        rag_rules = [{
            "section_number": ch["section_number"],
            "section_title": ch["chapter_title"],
            "clause_number": f"п.{ch['section_number']}",
            "paragraph_text": ch["body"],
            "topic": ch["chapter_title"]
        } for ch in chapters]

        with open(self.output_json, "w", encoding="utf-8") as f:
            json.dump(rag_rules, f, ensure_ascii=False, indent=2)

        duration = round(time.time() - t0, 2)
        self.logger.info(f"✅ ПДД РФ успешно обработаны и сохранены:")
        self.logger.info(f"  • JSONL глав: {self.output_chapters} ({len(chapters)} глав)")
        self.logger.info(f"  • RAG JSON:   {self.output_json}")
        self.logger.info("=" * 70)

        if test_mode and chapters:
            print(f"\n[ТЕСТОВЫЙ ПРОГОН ПДД УСПЕШЕН]: Обработана '{chapters[0]['title']}' ({len(chapters[0]['body'])} симв.)")

        return {
            "items_collected": len(chapters),
            "output_chapters_jsonl": str(self.output_chapters),
            "output_file": str(self.output_json),
            "duration_sec": duration
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Тестовый запуск коллектора ПДД РФ")
    parser.add_argument("--test", action="store_true", help="Запустить проверку на 1 главе")
    args = parser.parse_args()

    collector = PDDCollector()
    asyncio.run(collector.collect(test_mode=args.test or True))
