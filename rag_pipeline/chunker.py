"""
Иерархический чанкинг (Parent-Document / Small-to-Big).
Разбивает тяжелые 20 000 статей и постановлений ВС РФ на компактные
семантические фрагменты для точного поиска, сохраняя связь с полным контекстом.
"""

import json
import re
from typing import Any, Dict, List, Tuple
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None

from rag_pipeline.config import (
    CARS_DIR,
    COURT_DIR,
    LEGAL_CHAPTERS_FILE,
    LEGAL_DIR,
    LEGAL_JSONL_FILE,
    NEWS_DIR,
    PDD_CHAPTERS_FILE,
    PDD_DIR,
    PDD_PDF_URL,
    PDD_RULES_FILE,
)


def split_text_into_clauses(text: str, max_chars: int = 400, min_chars: int = 80) -> List[str]:
    """
    Разбивает юридический текст на смысловые пункты и абзацы,
    отсекая мусорные пустые строки.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []

    for para in paragraphs:
        # Если абзац слишком длинный — делим по предложениям
        if len(para) > max_chars:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            curr = ""
            for s in sentences:
                if len(curr) + len(s) < max_chars:
                    curr = f"{curr} {s}".strip()
                else:
                    if len(curr) >= min_chars:
                        chunks.append(curr)
                    curr = s
            if len(curr) >= min_chars:
                chunks.append(curr)
        elif len(para) >= min_chars:
            chunks.append(para)

    return chunks if chunks else [text[:max_chars]]


class RAGChunker:
    """Универсальный чанкер для всех 4 источников данных"""

    @staticmethod
    def chunk_legal_docs() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Чанкинг нормативной базы (ГК РФ / НК РФ / КоАП РФ).
        Читает из единого JSONL файла: data/legal/laws_gk_nk.jsonl
        с поддержкой префиксов:
          - tax_ (если section == "НК РФ")
          - civics_ (если section == "ГК РФ")
          - exec_ (если section == "КоАП РФ")
          - other_ (для остальных)
        """
        child_chunks = []
        parent_store = {}

        # 1. Чтение из структурированного файла по статьям и главам (LEGAL_CHAPTERS_FILE)
        target_file = LEGAL_CHAPTERS_FILE if LEGAL_CHAPTERS_FILE.exists() else LEGAL_JSONL_FILE
        if target_file.exists():
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            doc = json.loads(line)

                            section = doc.get("section", "ГК РФ")

                            # Определение префикса по вашему правилу
                            if section == "НК РФ":
                                prefix = "tax"
                            elif section == "КоАП РФ":
                                prefix = "exec"
                            elif section == "ГК РФ":
                                prefix = "civics"
                            else:
                                prefix = "other"

                            code = doc.get("code") or section
                            chapter_num = doc.get("chapter_number", "")
                            art_num = doc.get("article_number", "")
                            title = doc.get("title", f"{code} {art_num}" if art_num else f"Документ #{line_idx}")
                            category = doc.get("category", "Нормативная база")

                            # Генерация parent_id с учетом префикса, если он отсутствует или требует стандартизации
                            raw_pid = doc.get("parent_id") or doc.get("doc_id")
                            if raw_pid and raw_pid.startswith(("tax_", "civics_", "exec_", "other_")):
                                parent_id = raw_pid
                            else:
                                art_num_clean = re.sub(r'[^\d]', '', art_num) or str(line_idx)
                                ch_num_clean = re.sub(r'[^\d]', '', chapter_num) or "1"
                                parent_id = f"{prefix}_ch{ch_num_clean}_art{art_num_clean}"

                            local_doc_id = doc.get("local_doc_id", f"legal_{parent_id}")
                            url = doc.get("url") or f"#doc-legal_{parent_id}"
                            details = doc.get("details", "")
                            priority = doc.get("priority_level", "high" if any(k in title.lower() for k in
                                                                               ["аренд", "лизинг", "транспорт", "налог",
                                                                                "субаренд"]) else "standard")
                            collected_at = doc.get("collected_at", "")
                            body = doc.get("body", doc.get("full_text", ""))

                            # Сохраняем родительский документ со всеми реквизитами
                            parent_store[parent_id] = {
                                "parent_id": parent_id,
                                "doc_id": parent_id,
                                "local_doc_id": local_doc_id,
                                "source_site": doc.get("source_site", "docs.cntd.ru"),
                                "code": code,
                                "chapter_number": chapter_num,
                                "article_number": art_num,
                                "section": section,
                                "category": category,
                                "original_url": doc.get("original_url", doc.get("url", "https://docs.cntd.ru")),
                                "url": url,
                                "title": title,
                                "details": details,
                                "collected_at": collected_at,
                                "priority_level": priority,
                                "full_text": body
                            }

                            # Извлекаем пункты (small chunks) для точного поиска
                            clauses = split_text_into_clauses(body, max_chars=450, min_chars=60)
                            for idx, clause in enumerate(clauses):
                                chunk_id = f"{parent_id}_c{idx}"
                                searchable_text = f"{code} | {chapter_num} | {title} ({category}). {clause}"
                                child_chunks.append({
                                    "id": chunk_id,
                                    "parent_id": parent_id,
                                    "text": searchable_text,
                                    "metadata": {
                                        "parent_id": parent_id,
                                        "local_doc_id": local_doc_id,
                                        "code": code,
                                        "chapter_number": chapter_num,
                                        "article_number": art_num,
                                        "section": section,
                                        "category": category,
                                        "title": title,
                                        "url": url,
                                        "details": details,
                                        "priority_level": priority,
                                        "collected_at": collected_at,
                                        "doc_type": "legal_law",
                                        "chunk_index": idx
                                    }
                                })
                        except Exception:
                            continue
            except Exception:
                pass

        # 2. Резервный поиск в .md файлах, если JSONL не найден
        if not parent_store and LEGAL_DIR.exists():
            for file_path in LEGAL_DIR.glob("*.md"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    meta = {}
                    body = content
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            if yaml:
                                meta = yaml.safe_load(parts[1]) or {}
                            else:
                                meta = {}
                                for mline in parts[1].split("\n"):
                                    if ":" in mline:
                                        k, v = mline.split(":", 1)
                                        meta[k.strip()] = v.strip().strip('"').strip("'")
                            body = parts[2].strip()

                    section = meta.get("section", "ГК РФ")
                    if "нк" in section.lower() or "налог" in section.lower():
                        section = "НК РФ"
                        prefix = "tax"
                    elif "коап" in section.lower():
                        section = "КоАП РФ"
                        prefix = "exec"
                    elif "гк" in section.lower():
                        section = "ГК РФ"
                        prefix = "civics"
                    else:
                        prefix = "other"

                    parent_id = f"{prefix}_{file_path.stem}"
                    title = meta.get("title", file_path.stem)
                    url = meta.get("original_url", "https://docs.cntd.ru")
                    details = meta.get("details", "")
                    priority = meta.get("priority_level", "standard")
                    category = meta.get("category", "Нормативная база")

                    parent_store[parent_id] = {
                        "parent_id": parent_id,
                        "title": title,
                        "url": url,
                        "details": details,
                        "priority_level": priority,
                        "category": category,
                        "section": section,
                        "full_text": body
                    }

                    clauses = split_text_into_clauses(body, max_chars=450, min_chars=70)
                    for idx, clause in enumerate(clauses):
                        chunk_id = f"{parent_id}_c{idx}"
                        searchable_text = f"{section} | {title}. {clause}"
                        child_chunks.append({
                            "id": chunk_id,
                            "parent_id": parent_id,
                            "text": searchable_text,
                            "metadata": {
                                "parent_id": parent_id,
                                "section": section,
                                "title": title,
                                "url": url,
                                "details": details,
                                "priority_level": priority,
                                "category": category,
                                "doc_type": "legal_law",
                                "chunk_index": idx
                            }
                        })
                except Exception:
                    continue

        return child_chunks, parent_store

    @staticmethod
    def chunk_court_docs() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Чанкинг судебной практики ВС РФ с фильтрацией бюрократического шума:
        1. Удаление «шапок» судов, ФИО судей/секретарей и процедурного протокола.
        2. Отсечение непрофильных сфер права (чисто земельные споры по ЗК РФ, жилье, уголовные дела).
        3. Вырезка только мотивировочных и резолютивных частей (правовые позиции коллегий).
        4. Добавление тегов категорий в метаданные ChromaDB для точечного поиска.
        """
        child_chunks = []
        parent_store = {}

        court_file = COURT_DIR / "vsrf_court_docs_rag.json"
        if not court_file.exists():
            return child_chunks, parent_store

        # Регулярные выражения процедурного шума
        procedural_noise_pattern = re.compile(
            r'^(?:'
            r'в\s+составе\s+председательствующ|'
            r'председательствующего|'
            r'судей\s+верховного|'
            r'при\s+секретаре|'
            r'секретаре\s+судебного|'
            r'с\s+участием\s+представител|'
            r'с\s+участием\s+прокурора|'
            r'протокол\s+вел|'
            r'по\s+доверенности\s+от|'
            r'рассмотрела\s+в\s+открытом\s+судебном|'
            r'рассмотрев\s+в\s+судебном\s+заседании|'
            r'заслушав\s+доклад\s+судьи|'
            r'руководствуясь\s+статьями\s+(?:390|291|328|329)|'
            r'ходатайство\s+об\s+отложении|'
            r'определил\s+отложить|'
            r'дело\s+направлено\s+для\s+рассмотрения\s+в\s+суд'
            r')',
            re.IGNORECASE
        )

        irrelevant_land_or_housing_pattern = re.compile(
            r'(?:земельный\s+участок|земельного\s+участка|ст\.\s*22\s*зк\s*рф|кадастровый\s+номер|'
            r'межевани|долевое\s+строительство|многоквартирный\s+дом|жилое\s+помещение|приватизация\s+квартиры|'
            r'расторжение\s+брака|алименты)',
            re.IGNORECASE
        )

        automotive_or_movable_pattern = re.compile(
            r'(?:автомобил|транспортн|лизинг|раскат|выкуп|аренд|субаренд|тс\b|страхов|осаго|каско|'
            r'дтп|гибдд|штраф|водитель|сальдо|убытк|неустойк|движимо|залог)',
            re.IGNORECASE
        )

        # Ключевые маркеры мотивировочной части (суть правовой позиции суда)
        motivational_markers = [
            "суд указал", "коллегия пришла к выводу", "коллегия полагает", "коллегия находит",
            "по смыслу", "в силу статьи", "в силу положений", "в соответствии со стать",
            "судам следует", "как разъяснено", "позиция верховного суда", "пленум верховного суда",
            "бремя доказывания", "недействительн", "расторжен", "изъяти", "субаренд", "поднаем",
            "согласие арендодателя", "лизинг", "выкуп", "транспортн", "автомобил", "убытк",
            "неустойк", "сальдо", "страхов", "осаго", "каско", "залог", "виндикац",
            "возврат", "потребител", "зозпп", "штраф", "дтп", "определила:", "постановил:",
            "взыскать", "отменить судебные акты", "направить на новое рассмотрение"
        ]

        def get_category_tag(txt: str) -> str:
            t = txt.lower()
            if any(k in t for k in ["субаренд", "поднаем", "передача третьим", "без согласия"]):
                return "Субаренда и передача ТС третьим лицам"
            if any(k in t for k in ["лизинг", "лизингополучател", "раскат", "выкуп", "ст. 665", "ст. 624"]):
                return "Лизинг и раскат (выкуп) автомобиля"
            if any(k in t for k in ["расторжен", "возврат тс", "изъяти", "ст. 619", "ст. 622", "ст. 450"]):
                return "Расторжение договора и возврат ТС"
            if any(k in t for k in ["сальдо", "встречных обязательств", "банкрот"]):
                return "Расчет сальдо и банкротство"
            if any(k in t for k in ["страхов", "осаго", "каско", "дтп", "ущерб", "страховщик"]):
                return "Страхование (ОСАГО/КАСКО) и ущерб при ДТП"
            if any(k in t for k in ["потребител", "зозпп", "недостатк", "гаранти"]):
                return "Защита прав потребителей"
            return "Судебная практика по аренде и обязательствам"

        try:
            with open(court_file, "r", encoding="utf-8") as f:
                cases = json.load(f)

            for idx, item in enumerate(cases):
                meta = item.get("metadata", {})
                content = item.get("page_content", "")

                parent_id = f"court_{idx}"
                title = meta.get("title", f"Дело ВС РФ #{idx}")
                case_num = meta.get("case_number", "Не указан")
                date = meta.get("date", "Не указана")
                url = meta.get("url", "https://www.vsrf.ru")

                parent_store[parent_id] = {
                    "parent_id": parent_id,
                    "title": title,
                    "case_number": case_num,
                    "date": date,
                    "url": url,
                    "full_text": content
                }

                # Разбиение на смысловые пункты с отсечением бюрократического шума
                raw_clauses = split_text_into_clauses(content, max_chars=480, min_chars=90)
                kept_idx = 0

                for clause in raw_clauses:
                    clause_clean = clause.strip()
                    if len(clause_clean) < 80:
                        continue

                    # 1. Отсекаем «шапки» и процессуальный шум
                    if procedural_noise_pattern.search(clause_clean):
                        continue

                    # 2. Отсекаем непрофильные споры (земля / долевое жилье без авто/лизинга)
                    if irrelevant_land_or_housing_pattern.search(clause_clean) and not automotive_or_movable_pattern.search(clause_clean):
                        continue

                    # 3. Проверяем мотивировочную / смысловую ценность
                    clause_lower = clause_clean.lower()
                    has_motivational = any(m in clause_lower for m in motivational_markers)
                    is_procedural_history_only = (
                        ("обратился в суд" in clause_lower or "решением суда от" in clause_lower)
                        and not has_motivational
                    )
                    if is_procedural_history_only:
                        continue

                    # 4. Если абзац содержит правовую позицию или вывод суда — сохраняем с категорией
                    if has_motivational or automotive_or_movable_pattern.search(clause_clean):
                        cat_tag = get_category_tag(clause_clean)
                        chunk_id = f"{parent_id}_c{kept_idx}"
                        searchable_text = f"Судебная практика ВС РФ | {title} (Дело {case_num}, {cat_tag}). {clause_clean}"

                        child_chunks.append({
                            "id": chunk_id,
                            "parent_id": parent_id,
                            "text": searchable_text,
                            "metadata": {
                                "parent_id": parent_id,
                                "title": title,
                                "case_number": case_num,
                                "date": date,
                                "url": url,
                                "category": cat_tag,
                                "category_tag": cat_tag,
                                "doc_type": "court_decision",
                                "priority_level": "high",  # Практика ВС РФ имеет высокий авторитет
                                "chunk_index": kept_idx
                            }
                        })
                        kept_idx += 1

        except Exception as e:
            logger.error(f"Ошибка при чанкинге судебных актов ВС РФ: {e}")

        return child_chunks, parent_store

    @staticmethod
    def chunk_cars_catalog() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Чанкинг каталога автомобилей raskatof.ru.
        Поддерживает как schema с 'model', так и 'title'/'name',
        'specifications' и 'specs', 'leasing_terms' (dict или str).
        Каждая карточка авто является неделимым атомарным чанком.
        """
        child_chunks = []
        parent_store = {}

        cars_file = CARS_DIR / "cars_raskatof.json"
        if not cars_file.exists():
            return child_chunks, parent_store

        try:
            with open(cars_file, "r", encoding="utf-8") as f:
                cars = json.load(f)

            for idx, car in enumerate(cars):
                parent_id = f"car_{idx}"
                # Совместимость по названию модели (cars_raskatof.json: model, другие: title/name)
                model_name = car.get("model") or car.get("title") or car.get("name") or f"Автомобиль #{idx}"
                category = car.get("category", "Эконом и комфорт класс")

                # Обработка условий лизинга / раската
                terms = car.get("leasing_terms") or car.get("leasing_info") or {}
                if isinstance(terms, dict):
                    daily = terms.get("daily_rate") or terms.get("daily") or terms.get("rate") or terms.get("terms_text") or "По запросу"
                    initial = terms.get("initial_payment") or terms.get("initial") or terms.get("first_payment") or "Без первого взноса"
                elif isinstance(terms, str):
                    daily = terms
                    initial = "уточняйте у менеджера"
                else:
                    daily = str(car.get("daily_rate", "По запросу"))
                    initial = str(car.get("initial_payment", "Без первого взноса"))

                # Характеристики: specifications или specs
                specs = car.get("specifications") or car.get("specs") or {}
                if isinstance(specs, dict):
                    specs_str = ", ".join([f"{k}: {v}" for k, v in specs.items()])
                elif isinstance(specs, list):
                    specs_str = ", ".join(str(s) for s in specs)
                else:
                    specs_str = str(specs)

                # Комплектация и опции: features или options
                features = car.get("features") or car.get("options") or []
                if isinstance(features, list):
                    features_str = "; ".join(features) if features else "стандартная комплектация"
                else:
                    features_str = str(features)

                url = car.get("source_url") or car.get("url") or "https://raskatof.ru/"
                updated_at = car.get("updated_at", "")

                formatted_text = (
                    f"Автомобиль: {model_name}\n"
                    f"Класс: {category}\n"
                    f"Характеристики: {specs_str}\n"
                    f"Опции и комплектация: {features_str}\n"
                    f"Условия раската (выкуп/аренда): аренда {daily}, первый взнос {initial}.\n"
                    f"Ссылка на авто: {url}"
                )

                parent_store[parent_id] = {
                    "parent_id": parent_id,
                    "title": model_name,
                    "model": model_name,
                    "url": url,
                    "source_url": url,
                    "daily_rate": daily,
                    "initial_payment": initial,
                    "category": category,
                    "specifications": specs,
                    "features": features,
                    "updated_at": updated_at,
                    "full_text": formatted_text
                }

                child_chunks.append({
                    "id": f"{parent_id}_c0",
                    "parent_id": parent_id,
                    "text": formatted_text,
                    "metadata": {
                        "parent_id": parent_id,
                        "title": model_name,
                        "model": model_name,
                        "url": url,
                        "source_url": url,
                        "category": category,
                        "daily_rate": daily,
                        "initial_payment": initial,
                        "doc_type": "car_item",
                        "priority_level": "high"
                    }
                })

        except Exception:
            pass

        return child_chunks, parent_store

    chunk_car_catalog = chunk_cars_catalog
    chunk_cars = chunk_cars_catalog
    chunk_car_catalog_chunks = chunk_cars_catalog
    chunk_cars_catalog_chunks = chunk_cars_catalog

    @staticmethod
    def chunk_pdd_rules() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Чанкинг Правил дорожного движения РФ (ПДД РФ).
        Читает структурированные главы (Главы 1–26, Основные положения по допуску ТС,
        Перечень неисправностей) из data/pdd/pdd_chapters.jsonl.
        Каждый смысловой пункт/абзац формирует точный поисковый чанк.
        """
        child_chunks = []
        parent_store = {}

        # 1. Чтение из структурированного JSONL по главам
        if PDD_CHAPTERS_FILE.exists():
            try:
                with open(PDD_CHAPTERS_FILE, "r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            doc = json.loads(line)
                            parent_id = doc.get("parent_id") or doc.get("doc_id") or f"pdd_{line_idx}"
                            sec_num = doc.get("section_number", line_idx)
                            ch_num = doc.get("chapter_number", f"Глава {sec_num}")
                            ch_title = doc.get("chapter_title", "")
                            title = doc.get("title", f"ПДД РФ: {ch_title}")
                            category = doc.get("category", "Правила дорожного движения РФ")
                            local_doc_id = doc.get("local_doc_id", f"pdd_{parent_id}")
                            url = doc.get("url") or f"#doc-pdd_{parent_id}"
                            priority = doc.get("priority_level", "high")
                            body = doc.get("body", doc.get("full_text", ""))

                            parent_store[parent_id] = {
                                "parent_id": parent_id,
                                "doc_id": parent_id,
                                "local_doc_id": local_doc_id,
                                "section_number": sec_num,
                                "chapter_number": ch_num,
                                "chapter_title": ch_title,
                                "title": title,
                                "category": category,
                                "url": url,
                                "original_url": doc.get("original_url", PDD_PDF_URL),
                                "priority_level": priority,
                                "full_text": body
                            }

                            clauses = split_text_into_clauses(body, max_chars=450, min_chars=60)
                            for idx, clause in enumerate(clauses):
                                chunk_id = f"{parent_id}_c{idx}"
                                searchable_text = f"ПДД РФ | {ch_title}. {clause}"
                                child_chunks.append({
                                    "id": chunk_id,
                                    "parent_id": parent_id,
                                    "text": searchable_text,
                                    "metadata": {
                                        "parent_id": parent_id,
                                        "local_doc_id": local_doc_id,
                                        "section": ch_title,
                                        "chapter_number": ch_num,
                                        "chapter_title": ch_title,
                                        "title": title,
                                        "url": url,
                                        "doc_type": "traffic_rules",
                                        "priority_level": priority,
                                        "chunk_index": idx
                                    }
                                })
                        except Exception:
                            continue
            except Exception:
                pass

        # 2. Резервное чтение из pdd_rules_rag.json при необходимости
        if not parent_store and PDD_RULES_FILE.exists():
            try:
                with open(PDD_RULES_FILE, "r", encoding="utf-8") as f:
                    rules = json.load(f)

                for idx, rule in enumerate(rules):
                    sec_num = rule.get("section_number", 1)
                    parent_id = f"pdd_ch{sec_num}"
                    sec_title = rule.get("section_title", "ПДД РФ")
                    clause = rule.get("clause_number", f"п.{idx}")
                    para_text = rule.get("paragraph_text", "")
                    topic = rule.get("topic", sec_title)
                    url = f"#doc-pdd_{parent_id}"
                    title = f"ПДД РФ | {sec_title}"

                    parent_store[parent_id] = {
                        "parent_id": parent_id,
                        "title": title,
                        "section_title": sec_title,
                        "clause_number": clause,
                        "topic": topic,
                        "url": url,
                        "full_text": para_text
                    }

                    searchable_text = f"ПДД РФ: {sec_title} | Пункт {clause} ({topic}). {para_text}"

                    child_chunks.append({
                        "id": f"{parent_id}_c0",
                        "parent_id": parent_id,
                        "text": searchable_text,
                        "metadata": {
                            "parent_id": parent_id,
                            "title": title,
                            "section": sec_title,
                            "clause": clause,
                            "topic": topic,
                            "url": url,
                            "doc_type": "traffic_rules",
                            "priority_level": "high"
                        }
                    })

            except Exception:
                pass

        return child_chunks, parent_store

    chunk_pdd = chunk_pdd_rules

    @staticmethod
    def chunk_news_docs() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Чанкинг автомобильных новостей.
        """
        child_chunks = []
        parent_store = {}

        news_file = NEWS_DIR / "latest_autonews.json"
        if not news_file.exists():
            return child_chunks, parent_store

        try:
            with open(news_file, "r", encoding="utf-8") as f:
                articles = json.load(f)

            for idx, art in enumerate(articles):
                parent_id = f"news_{idx}"
                meta = art.get("metadata", {})
                title = meta.get("title", f"Новость #{idx}")
                content = art.get("page_content", "")
                url = meta.get("url", "#")
                date = meta.get("date", "")
                source = meta.get("source", "СМИ")

                parent_store[parent_id] = {
                    "parent_id": parent_id,
                    "title": title,
                    "url": url,
                    "date": date,
                    "source": source,
                    "full_text": content
                }

                clauses = split_text_into_clauses(content, max_chars=400, min_chars=60)
                for c_idx, clause in enumerate(clauses):
                    child_chunks.append({
                        "id": f"{parent_id}_c{c_idx}",
                        "parent_id": parent_id,
                        "text": f"{title}. {clause}",
                        "metadata": {
                            "parent_id": parent_id,
                            "title": title,
                            "url": url,
                            "date": date,
                            "source": source,
                            "doc_type": "news_article",
                            "priority_level": "medium",
                            "chunk_index": c_idx
                        }
                    })

        except Exception:
            pass

        return child_chunks, parent_store

    chunk_auto_news = chunk_news_docs
