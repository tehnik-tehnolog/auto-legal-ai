"""
Hierarchical chunking (Parent-Document / Small-to-Big).
Splits ~20,000 legal articles and Supreme Court rulings into compact semantic chunks
for accurate retrieval while preserving full parent document context.
"""

import json
import logging
import re
from typing import Any, Dict, List, Tuple
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger("rag_chunker")

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


def split_article_into_chunks(text: str, max_chars: int = 400, min_chars: int = 80) -> List[str]:
    """
    Split a legal document by article boundaries.
    Short articles (<= max_chars) are kept intact as a single chunk.
    Larger articles are split into coherent fragments up to max_chars
    preserving paragraph and sentence boundaries (minimum min_chars).
    """
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [cleaned]

    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(para) > max_chars:
            # Flush accumulated buffer if non-empty
            if current_chunk:
                if len(current_chunk) >= min_chars:
                    chunks.append(current_chunk)
                current_chunk = ""
            # Split long paragraph by sentence boundaries
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(current_chunk) + len(s) + 1 <= max_chars:
                    current_chunk = f"{current_chunk} {s}".strip() if current_chunk else s
                else:
                    if len(current_chunk) >= min_chars:
                        chunks.append(current_chunk)
                    current_chunk = s
        else:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
            else:
                if len(current_chunk) >= min_chars:
                    chunks.append(current_chunk)
                current_chunk = para

    if current_chunk:
        if len(current_chunk) >= min_chars:
            chunks.append(current_chunk)
        elif chunks:
            # Merge short trailing remainder with previous chunk
            chunks[-1] = f"{chunks[-1]}\n\n{current_chunk}".strip()
        else:
            chunks.append(current_chunk)

    return chunks if chunks else [cleaned[:max_chars]]


def split_text_into_clauses(text: str, max_chars: int = 400, min_chars: int = 80) -> List[str]:
    """Split legal text into semantic clauses and paragraphs, discarding empty lines."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []

    for para in paragraphs:
        # Split oversized paragraphs by sentence boundaries
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
    """Unified hierarchical chunker for all knowledge base collections."""

    @staticmethod
    def chunk_legal_docs() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Chunk regulatory codes (Civil Code, Tax Code, Administrative Code, federal laws).
        Reads from data/legal/legal_chapters.jsonl or data/legal/laws_gk_nk.jsonl.
        """
        child_chunks = []
        parent_store = {}

        # 1. Read structured chapter/article JSONL (LEGAL_CHAPTERS_FILE)
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
                            parent_id = doc.get("parent_id") or doc.get("doc_id") or f"doc_{line_idx}"
                            code = doc.get("code") or ("НК РФ" if "tax" in parent_id or "налог" in doc.get("category", "").lower() else "ГК РФ")
                            chapter_num = doc.get("chapter_number", "")
                            art_num = doc.get("article_number", "")
                            title = doc.get("title", f"{code} {art_num}" if art_num else f"Документ #{line_idx}")
                            section = doc.get("section", code)
                            category = doc.get("category", "Нормативная база")
                            local_doc_id = doc.get("local_doc_id", f"legal_{parent_id}")
                            url = doc.get("url") or f"#doc-legal_{parent_id}"
                            details = doc.get("details", "")
                            priority = doc.get("priority_level", "high" if any(k in title.lower() for k in ["аренд", "лизинг", "транспорт", "налог", "субаренд"]) else "standard")
                            collected_at = doc.get("collected_at", "")
                            body = doc.get("body", doc.get("full_text", ""))

                            # Store full parent document with all metadata
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

                            # Chunk by article (keep whole article or split up to 400 chars)
                            clauses = split_article_into_chunks(body, max_chars=400, min_chars=80)
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

        # 2. Fallback to Markdown files if JSONL is unavailable
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

                    parent_id = f"civics_{file_path.stem}" if "665" in file_path.stem else f"tax_{file_path.stem}"
                    title = meta.get("title", file_path.stem)
                    url = meta.get("original_url", "https://docs.cntd.ru")
                    details = meta.get("details", "")
                    priority = meta.get("priority_level", "standard")
                    category = meta.get("category", "Нормативная база")
                    section = "НК РФ" if "нк" in category.lower() or "налог" in category.lower() else "ГК РФ"

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
        Chunk Supreme Court rulings while filtering out procedural boilerplate:
        1. Strip court headers, judge/clerk names, and procedural records.
        2. Exclude off-topic disputes (pure land, housing, family disputes without vehicle context).
        3. Keep reasoning and operative holdings.
        4. Tag chunks with domain categories for metadata filtering.
        """
        child_chunks = []
        parent_store = {}

        court_file = COURT_DIR / "vsrf_court_docs_rag.json"
        if not court_file.exists():
            return child_chunks, parent_store

        # Procedural boilerplate patterns to discard
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

        # Key markers of legal reasoning and judicial holdings
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

                # Split into semantic clauses while filtering procedural noise
                raw_clauses = split_text_into_clauses(content, max_chars=480, min_chars=90)
                kept_idx = 0

                for clause in raw_clauses:
                    clause_clean = clause.strip()
                    if len(clause_clean) < 80:
                        continue

                    # 1. Strip headers and procedural boilerplate
                    if procedural_noise_pattern.search(clause_clean):
                        continue

                    # 2. Drop off-topic land/housing disputes unrelated to vehicles or leasing
                    if irrelevant_land_or_housing_pattern.search(clause_clean) and not automotive_or_movable_pattern.search(clause_clean):
                        continue

                    # 3. Check for substantive legal reasoning
                    clause_lower = clause_clean.lower()
                    has_motivational = any(m in clause_lower for m in motivational_markers)
                    is_procedural_history_only = (
                        ("обратился в суд" in clause_lower or "решением суда от" in clause_lower)
                        and not has_motivational
                    )
                    if is_procedural_history_only:
                        continue

                    # 4. Keep clauses containing legal holdings or vehicle/leasing context
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
                                "priority_level": "high",  # Supreme Court rulings carry high authority
                                "chunk_index": kept_idx
                            }
                        })
                        kept_idx += 1

        except Exception as e:
            logger.error(f"Error chunking Supreme Court rulings: {e}")

        return child_chunks, parent_store

    @staticmethod
    def chunk_cars_catalog() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Chunk vehicle catalog from raskatof.ru.
        Supports schemas with 'model' or 'title'/'name', 'specifications' or 'specs',
        and 'leasing_terms' (dict or str). Each car card is kept as an atomic chunk.
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
                # Normalize model name across schema variants
                model_name = car.get("model") or car.get("title") or car.get("name") or f"Автомобиль #{idx}"
                category = car.get("category", "Эконом и комфорт класс")

                # Parse leasing/rental terms
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

                # Vehicle specifications
                specs = car.get("specifications") or car.get("specs") or {}
                if isinstance(specs, dict):
                    specs_str = ", ".join([f"{k}: {v}" for k, v in specs.items()])
                elif isinstance(specs, list):
                    specs_str = ", ".join(str(s) for s in specs)
                else:
                    specs_str = str(specs)

                # Trim features and options
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
        Chunk Russian Traffic Rules (PDD RF).
        Reads structured chapters (Chapters 1-26, vehicle admission rules, fault list)
        from data/pdd/pdd_chapters.jsonl, splitting paragraphs into retrieval chunks.
        """
        child_chunks = []
        parent_store = {}

        # 1. Read structured chapter JSONL
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

        # 2. Fallback to legacy pdd_rules_rag.json if JSONL is absent
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
        """Chunk automotive news articles."""
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
