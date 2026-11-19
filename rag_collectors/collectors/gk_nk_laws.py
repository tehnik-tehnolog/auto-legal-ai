import asyncio
import hashlib
import http.cookiejar
import json
import logging
import os
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

from collectors.base import BaseCollector
from config.settings import (
    CNTD_PRIMARY_LAWS,
    HTTP_TIMEOUT,
    LEGAL_CHAPTERS_FILE,
    LEGAL_DIR,
    LEGAL_JSONL_FILE,
    LOGS_DIR,
    USER_AGENT,
)

HIGH_PRIORITY_KEYWORDS = [
    "лизинг", "лизингополучат", "лизингодател", "финансов аренд",
    "аренда транспортн", "прокат", "раскат", "выкуп", "ремонт", "виндикаци", "агрегат", "угон",
    "транспортн налог", "регистрац транспортн", "регистраци ТС", "собственник транспортн",
    "пдд", "транспортн средств", "осаго",  "обязательн страхов", "каско", "добровольн страхов"
]

MEDIUM_PRIORITY_KEYWORDS = [
    "залог", "удержан вещ", "обеспечен исполнен",
    "неустойк", "упущенн выгод",
    "истребован из чуж", "ндс", "налог на прибыль", "расход учет", "капитальн ремонт",
    "амортизац", "налог на имуществен", "безопасност дорожн",
    "регрессн требован", "суброгац",
    "гибел имуществен", "штраф", "автоматическ режим",
    "банкротств", "финансово управляющ",
    "потребител", "самоуправств", "неправомерн завладен", "конфискац"
]


def determine_priority(title: str, text: str) -> str:
    """Определение приоритета документа для RAG в компании по раскату авто"""
    combined = (title + " " + text[:600]).lower()
    if any(k in combined for k in HIGH_PRIORITY_KEYWORDS):
        return "high"
    if any(k in combined for k in MEDIUM_PRIORITY_KEYWORDS):
        return "medium"
    return "standard"


def roman_to_int(roman_str: str) -> Optional[int]:
    """Преобразование римских цифр (I, II, III, IV...) в арабские числа"""
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    s = roman_str.upper().strip()
    if not s or not re.match(r'^[IVXLCDM]+$', s):
        return None
    res = 0
    for i in range(len(s)):
        val = roman_map.get(s[i], 0)
        if i + 1 < len(s) and val < roman_map.get(s[i + 1], 0):
            res -= val
        else:
            res += val
    return res if res > 0 else None


class LawsCollector(BaseCollector):
    """
    Коллектор нормативно-правовой базы (ГК РФ, НК РФ, КоАП РФ, законы об авто и лизинге).
    Разбивает законы по статьям (1 статья = 1 документ) и сохраняет в:
      - data/legal/legal_chapters.jsonl
      - data/legal/laws_gk_nk.jsonl
    """

    def __init__(self):
        super().__init__("laws_gk_nk")
        self.output_chapters = LEGAL_CHAPTERS_FILE
        self.output_jsonl = LEGAL_JSONL_FILE
        self.output_dir = LEGAL_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = LOGS_DIR / "laws_collector_detailed.log"
        self.cache_dir = LEGAL_DIR / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def clean_legal_text(text: str) -> str:
        """
        Очистка и форматирование юридического текста статьи (как в pdd.py):
        - Замена конструкции <*> на текст из сноски (курсивом).
        - Устранение переносов слов через дефис.
        - Склейка одиночных переносов строк в связные абзацы.
        - Выделение слов в кавычках жирным шрифтом (**"..."** / **«...»**).
        - Выделение пунктов (*1.*, *2.1.*, *1)* и т.д.) курсивом.
        """
        if not text:
            return ""

        # 1. Сноски <*>
        footnote_pattern = r'--------------------------------\s*<\*>\s*([^\n]+)'
        match_fn = re.search(footnote_pattern, text)
        if match_fn:
            fn_text = match_fn.group(1).strip()
            text = re.sub(footnote_pattern, '', text)
            text = text.replace('<*>', f'*{fn_text}*')

        text = re.sub(r'-{3,}', '', text)

        # 2. Переносы через дефис
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)

        # 3. Одиночные переносы строк на пробелы
        clean_pattern = r'(?<!\n)\n(?!\n|\s*["\'«„]|\s*[А-ЯЁA-Z]|\s*\d+(?:\.\d+)*\.?)'
        text = re.sub(clean_pattern, ' ', text)

        # 4. Двойные переносы для структурных абзацев
        text = re.sub(r'\n+', '\n\n', text)

        # 5. Множественные пробелы
        text = re.sub(r'[ \t]+', ' ', text)

        # 6. Слова в кавычках — жирным
        text = re.sub(r'"([^"]+)"', r'**"\1"**', text)
        text = re.sub(r'«([^»]+)»', r'**«\1»**', text)

        # 7. Нумерация пунктов — курсивом
        text = re.sub(r'(^|\n\n)(\d+\.|\d+\))', r'\1*\2*', text)

        return text.strip()

    @staticmethod
    def clean_html_to_text(html: str) -> str:
        """Преобразование HTML акта в чистый структурированный текст"""
        if not html:
            return ""
        # Сохраняем заголовки h1-h6 в одну строку
        html = re.sub(r'(<h[1-6][^>]*>.*?)(?:<br\s*/?>\s*)+(.*?)</h[1-6]>', r'\1 \2', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</?(?:p|div|h[1-6]|article|section)[^>]*>', '\n\n', html, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\n{3,}', '\n\n', text)
        lines = [re.sub(r'[ \t]+', ' ', line.strip()) for line in text.split('\n')]
        return '\n'.join(lines)

    def _fetch_law_raw_text(self, doc_url: str) -> str:
        """Скачивание или чтение из кэша текста акта с портала docs.cntd.ru"""
        doc_id_match = re.search(r'/document/(\d+)', doc_url)
        doc_id = doc_id_match.group(1) if doc_id_match else hashlib.md5(doc_url.encode()).hexdigest()[:8]
        cache_file = self.cache_dir / f"{doc_id}.txt"

        if cache_file.exists() and cache_file.stat().st_size > 500:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass

        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        # 1. Попытка скачивания через API blocks
        try:
            api_url = f"https://api.docs.cntd.ru/v1/document/{doc_id}"
            api_headers = {
                **headers,
                "Authorization": "Bearer 39dfb4bf-79ba-4916-aff1-849edc97a706",
                "X-Doc-Api-Key": "39dfb4bf-79ba-4916-aff1-849edc97a706"
            }
            req = urllib.request.Request(api_url, headers=api_headers)
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
                info = json.loads(r.read())
                b_info = info.get("data", {}).get("content", {}).get("text", {})
                blocks_cnt = b_info.get("blocks", 0) if isinstance(b_info, dict) else 0

                if blocks_cnt > 0:
                    self.logger.info(f"Загрузка {blocks_cnt} блоков API для документа {doc_id}...")
                    full_html = ""
                    for b in range(1, blocks_cnt + 1):
                        b_url = f"https://api.docs.cntd.ru/v1/document/{doc_id}/content/text/block/{b}"
                        b_req = urllib.request.Request(b_url, headers=api_headers)
                        try:
                            with urllib.request.urlopen(b_req, timeout=5) as b_res:
                                full_html += b_res.read().decode("utf-8", errors="ignore") + "\n\n"
                        except Exception:
                            break
                    if len(full_html) > 500:
                        raw_text = self.clean_html_to_text(full_html)
                        with open(cache_file, "w", encoding="utf-8") as f:
                            f.write(raw_text)
                        return raw_text
        except Exception as ex:
            self.logger.warning(f"API fetch fallback for {doc_id}: {ex}")

        # 2. Попытка скачивания веб-страницы
        try:
            cj = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            req = urllib.request.Request(doc_url, headers=headers)
            with opener.open(req, timeout=HTTP_TIMEOUT) as r:
                html = r.read().decode("utf-8", errors="ignore")
                raw_text = self.clean_html_to_text(html)
                if len(raw_text) > 500:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        f.write(raw_text)
                    return raw_text
        except Exception as ex:
            self.logger.warning(f"Direct HTML fetch fallback for {doc_url}: {ex}")

        return ""

    def parse_articles(self, raw_text: str, law_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Разбиение текста закона на статьи (1 статья = 1 документ).
        Связность: первое сочетание 'Глава N' формирует название и номер главы.
        Римские цифры глав преобразуются в арабские (Глава III -> Глава 3).
        Номера статей с нижним подчеркиванием или точками (Статья 50_1, Статья 50.1)
        корректно обрабатываются при формировании parent_id.
        """
        if not raw_text:
            return []

        # Регулярное выражение с поддержкой римских цифр глав и статей вида 50_1, 50.1, 12.31_1
        pattern = re.compile(
            r'(?P<chapter>(?:Глава|ГЛАВА)\s+(\d+|\b[IVXLCDM]+\b)\.?[ \t]*([^\n]*))|'
            r'(?P<article>(?:Статья|СТАТЬЯ)\s+(\d+(?:[._-]\d+)*)\.?[ \t]*([^\n]*))',
            re.MULTILINE
        )
        matches = list(pattern.finditer(raw_text))

        prefix = law_meta.get("prefix", "civics")
        code = law_meta.get("section", "Закон")
        cat = law_meta.get("category", "Законодательство")
        orig_url = law_meta.get("url", "https://docs.cntd.ru")
        details = law_meta.get("details", "")

        current_ch_num = "Глава 1"
        current_ch_title = "Глава 1. Общие положения"
        articles = []

        if matches:
            for idx, m in enumerate(matches):
                if m.group("chapter"):
                    ch_num_raw = m.group(2).strip()
                    ch_title_raw = m.group(3).strip()

                    # Преобразование римских цифр глав в арабские
                    r_val = roman_to_int(ch_num_raw)
                    ch_num_val = str(r_val) if r_val is not None else ch_num_raw

                    # Очистка названия главы от предшествующей цифры
                    clean_title = re.sub(r'^(?:[IVXLCDM]+|\d+)\.?\s*', '', ch_title_raw).strip()

                    current_ch_num = f"Глава {ch_num_val}"
                    current_ch_title = f"Глава {ch_num_val}. {clean_title}" if clean_title else f"Глава {ch_num_val}"

                elif m.group("article"):
                    art_num_val = m.group(5).strip()
                    art_title_val = m.group(6).strip()
                    if re.search(r'исключен[аы]?\b', art_title_val, re.IGNORECASE):
                        continue
                    start_body = m.end()
                    end_body = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
                    raw_body = raw_text[start_body:end_body]
                    cleaned_body = self.clean_legal_text(raw_body)

                    # Формирование безопасного ID с поддержкой 50_1, 50.1
                    ch_num_only = current_ch_num.replace("Глава ", "")
                    safe_ch = re.sub(r'[^a-zA-Z0-9]', '_', str(ch_num_only)).strip('_')
                    safe_art = re.sub(r'[^a-zA-Z0-9]', '_', str(art_num_val)).strip('_')
                    safe_art = re.sub(r'_+', '_', safe_art)
                    parent_id = f"{prefix}_ch{safe_ch}_art{safe_art}"

                    clean_art_title = re.sub(r'^(?:[._-]?\d+)*\.?\s*', '', art_title_val).strip()
                    display_art_title = clean_art_title if clean_art_title else art_title_val
                    art_title_str = f"Статья {art_num_val}. {display_art_title}" if display_art_title else f"Статья {art_num_val}"
                    full_title = f"{code}, {current_ch_num}. {art_title_str}"
                    priority = determine_priority(full_title, cleaned_body)

                    category_str = f"{code} ({current_ch_title.replace(current_ch_num + '. ', '')})" if current_ch_title else cat

                    articles.append({
                        "parent_id": parent_id,
                        "doc_id": parent_id,
                        "code": code,
                        "section": code,
                        "chapter_number": current_ch_num,
                        "chapter_title": current_ch_title,
                        "article_number": f"Статья {art_num_val}",
                        "article_title": display_art_title,
                        "title": full_title,
                        "category": category_str,
                        "original_url": orig_url,
                        "url": f"#doc-legal_{parent_id}",
                        "local_doc_id": f"legal_{parent_id}",
                        "priority_level": priority,
                        "details": details,
                        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "body": cleaned_body,
                        "full_text": f"# {full_title}\n\n**Кодекс:** {code} | **Раздел:** {current_ch_title}\n\n---\n\n{cleaned_body}"
                    })

        return articles

    async def collect(self, test_mode: bool = False, limit: int = None) -> Dict[str, Any]:
        t0 = time.time()
        self.logger.info("=" * 70)
        mode_str = "ТЕСТОВЫЙ ПРОГОН НА 1 ДОКУМЕНТЕ/СТАТЬЕ" if test_mode else "ПОЛНЫЙ СБОР БАЗЫ"
        self.logger.info(f"🚀 ЗАПУСК СБОРА НОРМАТИВНОЙ БАЗЫ СТАТЕЙ ({mode_str})")
        self.logger.info(f"Целевые файлы: {self.output_chapters} и {self.output_jsonl}")
        self.logger.info("=" * 70)

        target_laws = CNTD_PRIMARY_LAWS[:1] if test_mode else (CNTD_PRIMARY_LAWS[:limit] if limit else CNTD_PRIMARY_LAWS)
        all_articles = []

        for idx, law_item in enumerate(target_laws, 1):
            title = law_item["title"]
            url = law_item["url"]
            self.logger.info(f"\n[{idx}/{len(target_laws)}] Обработка акта: {title[:65]}...")

            raw_text = self._fetch_law_raw_text(url)
            parsed = self.parse_articles(raw_text, law_item)

            if parsed:
                self.logger.info(f"  ✅ Извлечено статей из документа: {len(parsed)} шт.")
                all_articles.extend(parsed[:1] if test_mode else parsed)
            else:
                self.logger.info(f"  ℹ️ Загружаем стандартную карточку акта...")
                parent_id = f"{law_item.get('prefix', 'civics')}_doc_{idx}"
                full_title = f"{law_item['section']} | {title}"
                body_text = self.clean_legal_text(
                    f"**Реквизиты:** {law_item.get('details', '')}\n\n"
                    f"**Раздел:** {law_item['section']} | **Категория:** {law_item['category']}\n\n"
                    f"Официальный текст акта доступен в карточке: [{title}]({url})"
                )
                all_articles.append({
                    "parent_id": parent_id,
                    "doc_id": parent_id,
                    "code": law_item["section"],
                    "section": law_item["section"],
                    "chapter_number": "Глава 1",
                    "chapter_title": "Глава 1. Общие положения",
                    "article_number": "Статья 1",
                    "article_title": title,
                    "title": full_title,
                    "category": law_item["category"],
                    "original_url": url,
                    "url": f"#doc-legal_{parent_id}",
                    "local_doc_id": f"legal_{parent_id}",
                    "priority_level": determine_priority(title, body_text),
                    "details": law_item.get("details", ""),
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "body": body_text,
                    "full_text": f"# {full_title}\n\n{body_text}"
                })

            if test_mode:
                break

        # Если all_articles сформированы — сохраняем в JSONL
        if all_articles:
            with open(self.output_chapters, "w", encoding="utf-8") as f_ch:
                for art in all_articles:
                    f_ch.write(json.dumps(art, ensure_ascii=False) + "\n")

            with open(self.output_jsonl, "w", encoding="utf-8") as f_jl:
                for art in all_articles:
                    f_jl.write(json.dumps(art, ensure_ascii=False) + "\n")

        duration = round(time.time() - t0, 2)
        self.logger.info("=" * 70)
        self.logger.info(f"✅ СБОР СТАТЕЙ ЗАВЕРШЕН ЗА {duration} СЕК")
        self.logger.info(f"Всего статей сохранено в {self.output_chapters}: {len(all_articles)} шт.")
        self.logger.info("=" * 70)

        return {
            "items_collected": len(all_articles),
            "output_file": str(self.output_chapters),
            "duration_sec": duration
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Запуск коллектора статей нормативной базы")
    parser.add_argument("--test", action="store_true", help="Запустить проверку на 1 документе/статье")
    args = parser.parse_args()

    collector = LawsCollector()
    asyncio.run(collector.collect(test_mode=args.test))

