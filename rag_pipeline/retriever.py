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
from rag_pipeline.indexer import ChromaRAGIndexer, SimpleBM25Index, lemmatize_text

logger = logging.getLogger("rag_retriever")
logger.setLevel(logging.INFO)


class QueryRouter:
    """
    Классификатор намерений пользователя (Query Router).
    Решает проблему Chunk Imbalance и ложных срабатываний:
    - Ищет авто (car_catalog) ТОЛЬКО при прямом указании конкретных марок/моделей
      или коммерческих ценовых запросов (цена, суточная ставка, каталог, взнос).
    - При юридических спорах (субаренда, расторжение, возврат ТС, статьи ГК/НК РФ)
      строго исключает car_catalog и направляет в legal_laws и court_cases.
    """

    # Конкретные марки и модели авто (латиница и кириллица)
    CAR_BRANDS_AND_MODELS = [
        "ford", "focus", "mondeo", "skoda", "octavia", "rapid", "kodiaq",
        "kia", "rio", "k5", "optima", "ceed", "cerato", "sportage", "sorento",
        "chery", "tiggo", "arrizo", "haval", "jolion", "f7", "dargo", "h9",
        "geely", "monjaro", "coolray", "atlas", "emgrand", "solaris",
        "hyundai", "creta", "elantra", "sonata", "tucson", "changan", "alsvin",
        "cs35", "cs55", "uni-v", "uni-k", "omoda", "c5", "s5", "exeed",
        "lx", "txl", "vx", "rx", "lada", "vesta", "granta", "largus", "niva",
        "москвич", "belgee", "toyota", "camry", "rav4", "corolla", "volkswagen",
        "polo", "jetta", "tiguan", "renault", "logan", "duster", "sandero",
        "nissan", "qashqai", "x-trail", "almera",
        # Кириллица
        "форд", "фокус", "мондео", "шкода", "октавия", "рапид", "киа", "рио",
        "к5", "оптима", "сид", "спортейдж", "чери", "тигго", "тиго", "арризо",
        "хавал", "хавейл", "джолион", "дарго", "ф7", "джили", "монджаро",
        "кулрей", "атлас", "эмгранд", "солярис", "хендай", "хёндэ", "крета",
        "элантра", "туссан", "тусон", "чанган", "омода", "эксид", "лада",
        "веста", "гранта", "ларгус", "нива", "тойота", "камри", "фольксваген",
        "поло", "тигуан", "рено", "логан", "дастер", "ниссан", "кашкай"
    ]

    # Коммерческие запросы каталога (цены, суточные ставки, комплектации, бронирование)
    CAR_COMMERCIAL = [
        "цена", "цены", "цену", "стоимост", "ставк", "суточн", "в сутки",
        "руб/сут", "первый взнос", "первоначальн", "ежемесячн", "в наличии",
        "бронирован", "забронироват", "выбрать авто", "подобрать авто",
        "каталог авто", "комплектац", "вариатор", "кпп", "автомат", "механика",
        "полный привод", "лошадин", "л.с."
    ]

    # Юридические сущности (законы, статьи, иски, споры, договоры)
    LEGAL_INTENT = [
        "стать", "ст.", "ст ", "гк рф", "нк рф", "коап", "зк рф", "апк", "гпк",
        "закон", "кодекс", "нормативн", "договор", "расторжен", "расторгнут",
        "суд", "иск", "исков", "субаренд", "поднаем", "неустойк", "убытк",
        "залог", "обязательств", "правовой", "юрист", "возврат тс", "изъяти",
        "взыскан", "ответственност", "банкрот", "пристав", "арбитраж",
        "претензи", "согласие арендодател", "перенаем", "вина", "сальдо"
    ]

    COURT_SPECIFIC = [
        "вс рф", "верховн", "дело №", "определени", "постановлени пленум",
        "судебн практик", "коллеги по гражданск", "коллеги по экономическ",
        "судебн акт", "жалоб", "кассацион"
    ]

    NEWS_KEYWORDS = [
        "новост", "утильсбор", "рынок", "динамик", "тенденци", "индексац",
        "автопром", "прогноз продаж"
    ]

    PDD_KEYWORDS = [
        "пдд", "правил дорожн", "скорост", "обгон", "знак", "разметк",
        "пешеход", "дтп", "светофор", "лишени прав", "помех справ",
        "детск кресл", "неисправност", "тормоз", "европротокол", "фары", "техосмотр"
    ]

    @classmethod
    def route(cls, query: str) -> List[str]:
        """
        Маршрутизация запросов по коллекциям базы знаний:
        - При словах-триггерах на ПДД -> traffic_rules (3) + legal_laws (2)
        - При словах-триггерах на новости -> auto_news (2) + legal_laws (3)
        - По умолчанию для всех юридических и общих вопросов -> legal_laws (4) + court_cases (1)
        (Триггеры на каталог авто отключены по требованию пользователя)
        """
        q = query.lower()
        has_pdd = any(k in q for k in cls.PDD_KEYWORDS)
        has_news = any(k in q for k in cls.NEWS_KEYWORDS)

        # 1. ПДД РФ (квота: 3 ПДД, 2 Нормативная база)
        if has_pdd:
            return [COLLECTION_PDD, COLLECTION_LAWS]

        # 2. Автоновости и рынок (квота: 2 новости, 3 Нормативная база)
        if has_news:
            return [COLLECTION_NEWS, COLLECTION_LAWS]

        # 3. Нормативная база и судебная практика (квота: 4 Нормативная база, 1 ВС РФ)
        return [COLLECTION_LAWS, COLLECTION_COURT]


class HybridRetriever:
    """
    Гибридный поисковый модуль:
    1. BM25 (морфологический лексический поиск с лемматизацией pymorphy3)
    2. Dense Vector (смысловой поиск в ChromaDB)
    3. RRF Слияние + Metadata Boost
    4. Cross-Encoder & Salience Re-ranking с сопоставлением нормализованных лемм
    5. Точный стратифицированный отбор 5 итоговых фрагментов по квотам:
       - 4 Нормативная база, 1 ВС РФ (по умолчанию)
       - 2 новости, 3 Нормативная база (при триггерах на новости)
       - 3 ПДД, 2 Нормативная база (при триггерах на ПДД)
    6. Parent-Document обогащение
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
                    similarity = max(0.0, 1.0 - dist)
                    meta = res["metadatas"][0][idx] if res.get("metadatas") else {}
                    doc_text = res["documents"][0][idx] if res.get("documents") else ""
                    results.append((c_id, similarity, meta, doc_text))
        except Exception as e:
            logger.debug(f"ChromaDB search fallback for {coll_name}: {e}")

        return results

    def _rerank_candidates(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Переранжирование (Cross-Encoder / Salience Re-ranking).
        Использует лемматизацию pymorphy3 для нахождения разных словоформ
        ('транспортный налог' <-> 'транспортного налога', 'гражданская ответственность' <-> 'гражданской ответственности').
        """
        q_lower = query.lower()
        q_lemmas = set(lemmatize_text(query))

        # Извлечение номеров статей из запроса (например: 615, 619, 624, 665, 450, 50_1, 50.1)
        article_numbers = set(re.findall(r'\b\d{1,4}(?:[._]\d+)?\b', q_lower))
        wants_articles = any(k in q_lower for k in ["стать", "ст.", "гк рф", "нк рф", "кодекс"])

        for item in candidates:
            text_str = item["text"] + " " + item.get("metadata", {}).get("title", "")
            doc_lemmas = set(lemmatize_text(text_str))
            coll = item.get("collection", "")

            # 1. Лексическое совпадение лемм (покрывает любые падежи и склонения)
            lemma_overlap = len(q_lemmas.intersection(doc_lemmas))
            lexical_multiplier = 1.0 + (min(lemma_overlap, 10) * 0.08)

            # 2. Бонус точного совпадения запрашиваемой статьи ГК/НК
            article_multiplier = 1.0
            if article_numbers:
                text_lower = item["text"].lower()
                for num in article_numbers:
                    num_clean = num.replace("_", ".").replace("-", ".")
                    if f"статья {num}" in text_lower or f"ст. {num}" in text_lower or f"статье {num}" in text_lower or f"статья {num_clean}" in text_lower:
                        article_multiplier += 0.35

            # 3. Приоритетный буст нормативной базы при юридическом вопросе
            norm_multiplier = 1.0
            if coll == COLLECTION_LAWS and wants_articles:
                norm_multiplier = 1.25

            # 4. Metadata Boost (высокоприоритетные нормы)
            priority = item.get("metadata", {}).get("priority_level", "standard")
            boost = PRIORITY_HIGH_BOOST if priority == "high" else (PRIORITY_MEDIUM_BOOST if priority == "medium" else 1.0)

            # Итоговый комбинированный балл реранкера (RRF базис)
            base_score = item.get("rrf_score", 0.02)
            item["rerank_score"] = round(base_score * boost * lexical_multiplier * article_multiplier * norm_multiplier, 4)

        # Сортировка по убыванию релевантности
        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        return reranked

    def _stratified_selection(self, query: str, ranked_candidates: List[Dict[str, Any]], target_collections: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Стратифицированный отбор строго по правилу состава итоговых 5 фрагментов:
        - По умолчанию: 4 Нормативная база (legal_laws), 1 ВС РФ (court_cases);
        - Если слова-триггеры на новости: 2 новости (auto_news), 3 Нормативная база (legal_laws);
        - Если слова-триггеры на ПДД: 3 ПДД (traffic_rules), 2 Нормативная база (legal_laws);
        - На авто пока не нужны триггеры.
        """
        q_lower = query.lower()
        has_pdd = any(k in q_lower for k in QueryRouter.PDD_KEYWORDS)
        has_news = any(k in q_lower for k in QueryRouter.NEWS_KEYWORDS)

        if has_pdd:
            quotas = [(COLLECTION_PDD, 3), (COLLECTION_LAWS, 2)]
        elif has_news:
            quotas = [(COLLECTION_NEWS, 2), (COLLECTION_LAWS, 3)]
        else:
            quotas = [(COLLECTION_LAWS, 4), (COLLECTION_COURT, 1)]

        by_coll: Dict[str, List[Dict[str, Any]]] = {}
        for item in ranked_candidates:
            c = item.get("collection", "")
            if c not in by_coll:
                by_coll[c] = []
            by_coll[c].append(item)

        selected = []
        selected_ids = set()

        # 1. Заполняем квоты (с приоритетом уникальных статей/документов по parent_id)
        for coll, count in quotas:
            items_for_coll = by_coll.get(coll, [])
            coll_selected = 0
            coll_parent_ids = set()

            # Первый проход: отбираем разные родительские статьи
            for item in items_for_coll:
                p_id = item.get("metadata", {}).get("parent_id", item["id"])
                if item["id"] not in selected_ids and p_id not in coll_parent_ids:
                    selected.append(item)
                    selected_ids.add(item["id"])
                    coll_parent_ids.add(p_id)
                    coll_selected += 1
                    if coll_selected >= count:
                        break

            # Второй проход: если уникальных статей меньше квоты, добираем чанки
            if coll_selected < count:
                for item in items_for_coll:
                    if item["id"] not in selected_ids:
                        selected.append(item)
                        selected_ids.add(item["id"])
                        coll_selected += 1
                        if coll_selected >= count:
                            break

        # 2. Если в какой-то коллекции не хватило документов до квоты,
        # добираем из общего пула кандидатов до 5 фрагментов
        if len(selected) < top_k:
            for item in ranked_candidates:
                if len(selected) >= top_k:
                    break
                if item["id"] not in selected_ids:
                    selected.append(item)
                    selected_ids.add(item["id"])

        return selected[:top_k]

    def retrieve(self, query: str, top_k: int = TOP_K_RERANK) -> Dict[str, Any]:
        """
        Основной метод выполнения RAG-поиска:
        Router -> BM25 + Dense -> RRF -> Boost -> Rerank -> Stratified Quota -> Parent Document Enrichment
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
        ranked_candidates = self._rerank_candidates(query, candidates_list)

        # 5. Стратифицированный отбор по квотам (гарантия присутствия статей ГК РФ)
        top_candidates = self._stratified_selection(query, ranked_candidates, target_collections, top_k=top_k)

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
