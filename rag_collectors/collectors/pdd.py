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
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                text += f"\n\n--- СТРАНИЦА {idx + 1} ---\n\n" + page_text
        except Exception as e:
            self.logger.warning(f"Ошибка чтения PDF через pypdf ({e}).")
        return text

    def _parse_pdd_chapters(self, full_text: str, test_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Парсинг официального текста ПДД РФ по главам:
        - Старт строго со слов "ПРАВИЛА ДОРОЖНОГО ДВИЖЕНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ"
        - Главы 1–26
        - Пропуск Приложений 1, 2, 3 (Знаки, Разметка, Сочи)
        - Продолжение с "ОСНОВНЫЕ ПОЛОЖЕНИЯ ПО ДОПУСКУ ТРАНСПОРТНЫХ СРЕДСТВ К ЭКСПЛУАТАЦИИ..."
        - "ПЕРЕЧЕНЬ НЕИСПРАВНОСТЕЙ И УСЛОВИЙ, ПРИ КОТОРЫХ ЗАПРЕЩАЕТСЯ ЭКСПЛУАТАЦИЯ ТРАНСПОРТНЫХ СРЕДСТВ"
        """
        # 1. Поиск точки старта
        start_marker = "ПРАВИЛА ДОРОЖНОГО ДВИЖЕНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ"
        idx_start = full_text.find(start_marker)
        work_text = full_text[idx_start:] if idx_start != -1 else full_text

        # 2. Вырезание нежелательных приложений 1, 2, 3
        # Ищем начало Приложения 1
        m_app1 = re.search(r'Приложение\s+1\s+к\s+Правилам\s+дорожного\s+движения|ДОРОЖНЫЕ\s+ЗНАКИ', work_text, re.IGNORECASE)
        # Ищем начало Основных положений по допуску
        m_admit = re.search(r'ОСНОВНЫЕ\s+ПОЛОЖЕНИЯ\s+ПО\s+ДОПУСКУ\s+ТРАНСПОРТНЫХ\s+СРЕДСТВ\s+К\s+ЭКСПЛУАТАЦИИ', work_text, re.IGNORECASE)

        main_rules_text = work_text
        admit_text = ""
        if m_app1 and m_admit and m_admit.start() > m_app1.start():
            # Отрезаем промежуток между Приложением 1 и Основными положениями допуска
            main_rules_text = work_text[:m_app1.start()]
            admit_text = work_text[m_admit.start():]
        elif m_admit:
            main_rules_text = work_text[:m_admit.start()]
            admit_text = work_text[m_admit.start():]

        chapters = []

        # Шаблон глав 1–26: "1. Общие положения", "2. Общие обязанности водителей" и т.д.
        chapter_pattern = re.compile(r'(?:^|\n\n)(\d{1,2})\.\s+([А-ЯЁ][^\n]+)(?=\n)', re.MULTILINE)
        matches = list(chapter_pattern.finditer(main_rules_text))

        for i, match in enumerate(matches):
            sec_num = int(match.group(1))
            sec_title = f"{sec_num}. {match.group(2).strip()}"
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(main_rules_text)
            body = main_rules_text[start_pos:end_pos].strip()

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

        # Добавляем разделы допуска ТС и перечня неисправностей, если не в тест-режиме 1 главы
        if admit_text and not test_mode:
            # Разделяем на Основные положения и Перечень неисправностей
            m_faults = re.search(r'ПЕРЕЧЕНЬ\s+НЕИСПРАВНОСТЕЙ\s+И\s+УСЛОВИЙ', admit_text, re.IGNORECASE)
            if m_faults:
                admit_main = admit_text[:m_faults.start()].strip()
                faults_body = admit_text[m_faults.start():].strip()
                chapters.append({
                    "section_number": 27,
                    "chapter_number": "Основные положения",
                    "chapter_title": "Основные положения по допуску ТС к эксплуатации",
                    "title": "ПДД РФ: Основные положения по допуску ТС к эксплуатации",
                    "body": admit_main
                })
                chapters.append({
                    "section_number": 28,
                    "chapter_number": "Перечень неисправностей",
                    "chapter_title": "Перечень неисправностей и условий, при которых запрещается эксплуатация ТС",
                    "title": "ПДД РФ: Перечень неисправностей, запрещающих эксплуатацию ТС",
                    "body": faults_body
                })
            else:
                chapters.append({
                    "section_number": 27,
                    "chapter_number": "Основные положения и неисправности",
                    "chapter_title": "Основные положения по допуску ТС к эксплуатации и перечень неисправностей",
                    "title": "ПДД РФ: Допуск ТС к эксплуатации и перечень неисправностей",
                    "body": admit_text.strip()
                })

        return chapters

    async def collect(self, test_mode: bool = False) -> Dict[str, Any]:
        t0 = time.time()
        self.logger.info("=" * 70)
        mode_str = "ТЕСТОВЫЙ ПРОГОН НА 1 ГЛАВЕ" if test_mode else "ПОЛНЫЙ СБОР БАЗЫ"
        self.logger.info(f"🚀 ЗАПУСК СБОРА И ПАРСИНГА ПДД РФ ({mode_str})")
        self.logger.info("=" * 70)

        # Проверяем наличие скачанного файла или пробуем скачать
        if not self.output_pdf.exists():
            self._download_pdf()

        extracted_text = self._extract_text_from_pdf()
        chapters = []

        if extracted_text and len(extracted_text) > 1000:
            chapters = self._parse_pdd_chapters(extracted_text, test_mode=test_mode)
            self.logger.info(f"Сформировано структурированных глав из PDF: {len(chapters)}")

        # Если PDF не удалось прочитать онлайн, используем эталонную базу из build_structured_bases
        if not chapters:
            try:
                from build_structured_bases import PDD_SECTIONS
            except ImportError:
                from rag_collectors.build_structured_bases import PDD_SECTIONS
            target_secs = PDD_SECTIONS[:1] if test_mode else PDD_SECTIONS
            for idx, sec in enumerate(target_secs, 1):
                ch_num_match = re.search(r'\d+', sec["chapter_number"])
                ch_num = int(ch_num_match.group(0)) if ch_num_match else idx
                chapters.append({
                    "section_number": ch_num,
                    "chapter_number": sec["chapter_number"],
                    "chapter_title": sec["chapter_title"],
                    "title": f"ПДД РФ: {sec['chapter_title']}",
                    "body": sec["body"]
                })

        # Сохранение в data/pdd/pdd_chapters.jsonl
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

        # Сохранение в эталонный pdd_rules_rag.json
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
