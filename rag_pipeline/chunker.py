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

from rag_pipeline.config import CARS_DIR, COURT_DIR, LEGAL_DIR, NEWS_DIR


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
        Чанкинг нормативной базы (ГК РФ / НК РФ).
        Возвращает:
            child_chunks: компактные фрагменты для векторного поиска
            parent_store: словарь полных статей с реквизитами для подачи в LLM
        """
        child_chunks = []
        parent_store = {}

        if not LEGAL_DIR.exists():
            return child_chunks, parent_store

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
                            for line in parts[1].split("\n"):
                                if ":" in line:
                                    k, v = line.split(":", 1)
                                    meta[k.strip()] = v.strip().strip('"').strip("'")
                        body = parts[2].strip()

                parent_id = f"law_{file_path.stem}"
                title = meta.get("title", file_path.stem)
                url = meta.get("original_url", "https://docs.cntd.ru")
                details = meta.get("details", "")
                priority = meta.get("priority_level", "standard")
                category = meta.get("category", "Нормативная база")

                # Сохраняем родительский документ целиком
                parent_store[parent_id] = {
                    "parent_id": parent_id,
                    "title": title,
                    "url": url,
                    "details": details,
                    "priority_level": priority,
                    "category": category,
                    "full_text": body
                }

                # Извлекаем пункты (small chunks) для поиска
                clauses = split_text_into_clauses(body, max_chars=450, min_chars=70)
                for idx, clause in enumerate(clauses):
                    chunk_id = f"{parent_id}_c{idx}"
                    # Добавляем название статьи к чанку для сохранения контекста
                    searchable_text = f"{title}. {clause}"
                    child_chunks.append({
                        "id": chunk_id,
                        "parent_id": parent_id,
                        "text": searchable_text,
                        "metadata": {
                            "parent_id": parent_id,
                            "title": title,
                            "url": url,
                            "details": details,
                            "priority_level": priority,
                            "category": category,
                            "doc_type": "legal_law",
                            "chunk_index": idx
                        }
                    })

            except Exception as e:
                continue

        return child_chunks, parent_store

    @staticmethod
    def chunk_court_docs() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Чанкинг судебной практики ВС РФ.
        """
        child_chunks = []
        parent_store = {}

        court_file = COURT_DIR / "vsrf_court_docs_rag.json"
        if not court_file.exists():
            return child_chunks, parent_store

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

                clauses = split_text_into_clauses(content, max_chars=500, min_chars=100)
                for c_idx, clause in enumerate(clauses):
                    chunk_id = f"{parent_id}_c{c_idx}"
                    child_chunks.append({
                        "id": chunk_id,
                        "parent_id": parent_id,
                        "text": clause,
                        "metadata": {
                            "parent_id": parent_id,
                            "title": title,
                            "case_number": case_num,
                            "date": date,
                            "url": url,
                            "doc_type": "court_decision",
                            "priority_level": "high",  # Практика ВС РФ всегда имеет высокий приоритет
                            "chunk_index": c_idx
                        }
                    })

        except Exception:
            pass

        return child_chunks, parent_store

    @staticmethod
    def chunk_cars_catalog() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Чанкинг каталога автомобилей raskatof.ru.
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
                model = car.get("model", "Автомобиль")
                category = car.get("category", "Эконом")
                terms = car.get("leasing_terms", {})
                daily = terms.get("daily_rate", "уточняйте")
                initial = terms.get("initial_payment", "уточняйте")
                specs = car.get("specifications", {})
                features = car.get("features", [])
                url = car.get("source_url", "https://raskatof.ru/")

                specs_str = ", ".join([f"{k}: {v}" for k, v in specs.items()])
                features_str = "; ".join(features) if features else "стандарт"

                formatted_text = (
                    f"Автомобиль: {model}\n"
                    f"Класс: {category}\n"
                    f"Характеристики: {specs_str}\n"
                    f"Опции: {features_str}\n"
                    f"Условия раската/выкупа: аренда {daily}, первый взнос {initial}.\n"
                    f"Ссылка: {url}"
                )

                parent_store[parent_id] = {
                    "parent_id": parent_id,
                    "title": model,
                    "url": url,
                    "daily_rate": daily,
                    "initial_payment": initial,
                    "category": category,
                    "full_text": formatted_text
                }

                child_chunks.append({
                    "id": f"{parent_id}_c0",
                    "parent_id": parent_id,
                    "text": formatted_text,
                    "metadata": {
                        "parent_id": parent_id,
                        "title": model,
                        "url": url,
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
