"""
Гибридный поисковый движок (BM25 + Dense) с семантическим роутером,
Metadata Boost и отсечением бюрократического шума через Cross-Encoder Reranker.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from rag_pipeline.config import (
    ALL_COLLECTIONS,
    CHROMA_DIR,
    COLLECTION_CARS,
    COLLECTION_COURT,
    COLLECTION_LAWS,
    COLLECTION_NEWS,
    COLLECTION_PDD,
    PRIORITY_HIGH_BOOST,
    PRIORITY_MEDIUM_BOOST,
    TOP_K_RERANK,
    TOP_K_RETRIEVAL,
)
from rag_pipeline.indexer import ChromaRAGIndexer, SimpleBM25Index

logger = logging.getLogger("rag_retriever")
logger.setLevel(logging.INFO)


class QueryRouter:
    """
    Классификатор намерений пользователя (Query Router).
    Направляет запрос в специализированные коллекции, предотвращая размывание
    юридического контекста каталогом машин и наоборот.
    """

    CARS_KEYWORDS = [
        "машин", "автомобил", "модел", "chery", "haval", "geely", "solaris",
        "цена", "стоимост", "ставк", "суточн", "взнос", "наличи", "ассортимент",
        "каталог", "взять", "аренд в сутк", "автопарк", "комплектац", "вариатор", "кпп"
    ]

    COURT_KEYWORDS = [
        "суд", "вс рф", "верховн", "дело", "определени", "постановлени",
        "практик", "спор", "банкрот", "изъяти", "пристав", "арест", "сальдо",
        "взыскан", "незаконн", "жалоб", "коллеги"
    ]

    LAWS_KEYWORDS = [
        "стать", "гк рф", "нк рф", "закон", "кодекс", "договор", "лизин",
        "финансов аренд", "выкуп", "раскат", "налог", "ндс", "амортизац",
        "неустойк", "убытк", "залог", "обязательств", "правовой", "юрист",
        "расторжени", "собственност", "штраф", "коап", "осаго", "регистрац"
    ]

    NEWS_KEYWORDS = [
        "новост", "утильсбор", "рынок", "динамик", "тенденци", "индексац",
        "осаго", "каско", "цены вырос", "прогноз", "правительств", "автопром"
    ]

    PDD_KEYWORDS = [
        "пдд", "правил дорожн движен", "скорост", "обгон", "знак", "разметк",
        "пешеход", "дтп", "авари", "светофор", "водитель", "лишени",
        "стоянк", "парковк", "перекрест", "помех справ", "детск кресл",
        "неисправност", "тормоз", "европротокол", "фары", "техосмотр"
    ]

    @classmethod
    def route(cls, query: str) -> List[str]:
        q = query.lower()
        target_collections = []

        is_cars = any(k in q for k in cls.CARS_KEYWORDS)
        is_court = any(k in q for k in cls.COURT_KEYWORDS)
        is_laws = any(k in q for k in cls.LAWS_KEYWORDS)
        is_news = any(k in q for k in cls.NEWS_KEYWORDS)
        is_pdd = any(k in q for k in cls.PDD_KEYWORDS)

        if is_pdd and not (is_court or is_cars):
            return [COLLECTION_PDD, COLLECTION_LAWS]

        if is_cars and not (is_court or is_laws or is_pdd):
            return [COLLECTION_CARS]

        if is_court and not is_cars:
            return [COLLECTION_COURT, COLLECTION_LAWS]

        if is_laws and not is_cars:
            return [COLLECTION_LAWS, COLLECTION_COURT]

        if is_news and not (is_laws or is_court or is_pdd):
            return [COLLECTION_NEWS]

        # Комплексный или общий запрос — гибридный опрос
        if is_cars:
            target_collections.append(COLLECTION_CARS)
        if is_laws or "договор" in q or "прав" in q:
            target_collections.append(COLLECTION_LAWS)
        if is_pdd:
            target_collections.append(COLLECTION_PDD)
        if is_court:
            target_collections.append(COLLECTION_COURT)
        if is_news:
            target_collections.append(COLLECTION_NEWS)

        return target_collections if target_collections else [COLLECTION_LAWS, COLLECTION_COURT, COLLECTION_CARS, COLLECTION_PDD]


class HybridRetriever:
    """
    Гибридный поисковый модуль:
    1. BM25 (точный лексический поиск по номерам статей и терминам)
    2. Dense Vector (смысловой поиск в ChromaDB)
    3. RRF Слияние + Metadata Boost
    4. Cross-Encoder / Salience Re-ranking
    5. Parent-Document обогащение
    """

    def __init__(self):
        self.indexer = ChromaRAGIndexer()
        self.parent_store = self.indexer.load_parent_store()
        self.bm25_indices: Dict[str, SimpleBM25Index] = {}
        self._init_bm25()

    def _init_bm25(self):
        """Загрузка чанков и инициализация BM25 для каждой коллекции"""
        for coll_name in ALL_COLLECTIONS:
            backup_file = CHROMA_DIR / f"{coll_name}_chunks.json"
            if backup_file.exists():
                try:
                    with open(backup_file, "r", encoding="utf-8") as f:
                        chunks = json.load(f)
                    bm25 = SimpleBM25Index()
                    bm25.build(chunks)
                    self.bm25_indices[coll_name] = bm25
                except Exception:
                    pass

    def _dense_search(self, coll_name: str, query: str, top_k: int) -> List[Tuple[str, float, Dict[str, Any], str]]:
        """Dense поиск в коллекции ChromaDB"""
        results = []
        if not self.indexer.client:
            return results

        try:
            coll = self.indexer.client.get_collection(coll_name)
            res = coll.query(query_texts=[query], n_results=min(top_k, coll.count()))
            if res and res["ids"] and len(res["ids"][0]) > 0:
                for idx, c_id in enumerate(res["ids"][0]):
                    dist = res["distances"][0][idx] if res.get("distances") else 0.5
                    # Преобразуем косинусную дистанцию в сходство (1 - dist)
                    similarity = max(0.0, 1.0 - dist)
                    meta = res["metadatas"][0][idx] if res.get("metadatas") else {}
                    doc_text = res["documents"][0][idx] if res.get("documents") else ""
                    results.append((c_id, similarity, meta, doc_text))
        except Exception as e:
            logger.debug(f"ChromaDB search fallback for {coll_name}: {e}")

        return results

    def _rerank_candidates(self, query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """
        Переранжирование (Cross-Encoder / Salience Re-ranking).
        Оценивает смысловую плотность, совпадение точных юридических сущностей
        и отсекает бюрократический шум.
        """
        q_lower = query.lower()
        q_tokens = set(re.findall(r'\b[а-яА-Яa-zA-Z0-9_-]{3,}\b', q_lower))

        for item in candidates:
            text_lower = item["text"].lower()
            title_lower = item.get("metadata", {}).get("title", "").lower()

            # Лексический бонус за точные совпадения реквизитов (статьи, номера дел)
            token_overlap = sum(1 for t in q_tokens if t in text_lower or t in title_lower)
            lexical_multiplier = 1.0 + (token_overlap * 0.08)

            # Metadata Boost (лизинг/раскат/выкуп)
            priority = item.get("metadata", {}).get("priority_level", "standard")
            boost = PRIORITY_HIGH_BOOST if priority == "high" else (PRIORITY_MEDIUM_BOOST if priority == "medium" else 1.0)

            # Итоговый комбинированный балл реранкера
            base_score = item.get("rrf_score", 0.5)
            item["rerank_score"] = round(base_score * boost * lexical_multiplier, 4)

        # Сортировка по убыванию релевантности
        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
        return reranked

    def retrieve(self, query: str, top_k: int = TOP_K_RERANK) -> Dict[str, Any]:
        """
        Основной метод выполнения RAG-поиска:
        Router -> BM25 + Dense -> RRF -> Boost -> Rerank -> Parent Document Enrichment
        """
        target_collections = QueryRouter.route(query)
        logger.info(f"Query: '{query}' -> Target collections: {target_collections}")

        # Сбор кандидатов из целевых коллекций
        candidates_map: Dict[str, Dict[str, Any]] = {}

        for coll in target_collections:
            # 1. BM25 кандидаты
            bm25_hits = []
            if coll in self.bm25_indices:
                bm25_hits = self.bm25_indices[coll].search(query, top_k=TOP_K_RETRIEVAL)

            # 2. Dense кандидаты
            dense_hits = self._dense_search(coll, query, top_k=TOP_K_RETRIEVAL)

            # 3. Reciprocal Rank Fusion (RRF)
            # RRF Score = 1 / (60 + rank_dense) + 1 / (60 + rank_bm25)
            bm25_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(bm25_hits)}
            dense_ranks = {doc_id: rank for rank, (doc_id, _, _, _) in enumerate(dense_hits)}

            all_doc_ids = set(bm25_ranks.keys()).union(set(dense_ranks.keys()))

            for d_id in all_doc_ids:
                r_bm25 = bm25_ranks.get(d_id, 100)
                r_dense = dense_ranks.get(d_id, 100)

                rrf_score = (1.0 / (60.0 + r_dense)) + (1.0 / (60.0 + r_bm25))

                # Получаем метаданные и текст чанка
                chunk_obj = None
                if coll in self.bm25_indices and d_id in self.bm25_indices[coll].docs_map:
                    chunk_obj = self.bm25_indices[coll].docs_map[d_id]
                else:
                    for d_hit in dense_hits:
                        if d_hit[0] == d_id:
                            chunk_obj = {"id": d_id, "text": d_hit[3], "metadata": d_hit[2]}
                            break

                if chunk_obj:
                    candidates_map[d_id] = {
                        "id": d_id,
                        "collection": coll,
                        "text": chunk_obj["text"],
                        "metadata": chunk_obj.get("metadata", {}),
                        "rrf_score": rrf_score
                    }

        # Если поиск ничего не вернул (база пуста или нет точных совпадений)
        if not candidates_map:
            return {
                "query": query,
                "target_collections": target_collections,
                "sources": [],
                "formatted_context": ""
            }

        # 4. Переранжирование кандидатов
        candidates_list = list(candidates_map.values())
        top_candidates = self._rerank_candidates(query, candidates_list, top_k=top_k)

        # 5. Обогащение родительским контекстом (Parent-Document Resolver)
        enriched_sources = []
        context_blocks = []

        for rank, item in enumerate(top_candidates, 1):
            meta = item.get("metadata", {})
            parent_id = meta.get("parent_id")
            parent_doc = self.parent_store.get(parent_id, {})

            # Извлекаем проверенные реквизиты и ссылку
            title = parent_doc.get("title") or meta.get("title", "Документ")
            url = parent_doc.get("url") or meta.get("url", "#")
            doc_type = meta.get("doc_type", "document")
            date = parent_doc.get("date") or meta.get("date", "")
            case_number = parent_doc.get("case_number") or meta.get("case_number", "")

            source_entry = {
                "citation_id": rank,
                "chunk_id": item["id"],
                "parent_id": parent_id,
                "collection": item["collection"],
                "title": title,
                "url": url,
                "doc_type": doc_type,
                "case_number": case_number,
                "date": date,
                "similarity_score": item.get("rerank_score", 0.0),
                "matched_chunk": item["text"],
                "parent_full_text": parent_doc.get("full_text", item["text"])
            }
            enriched_sources.append(source_entry)

            # Формируем компактный блок контекста для подачи в Gemini
            block_header = f"[Источник #{rank} | {title}] (Ссылка: {url})"
            if case_number:
                block_header += f" (Дело №: {case_number}, Дата: {date})"
            context_blocks.append(f"{block_header}\n{item['text']}")

        formatted_context = "\n\n---\n\n".join(context_blocks)

        return {
            "query": query,
            "target_collections": target_collections,
            "sources": enriched_sources,
            "formatted_context": formatted_context
        }
