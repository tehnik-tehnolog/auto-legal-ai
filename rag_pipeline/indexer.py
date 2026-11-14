"""
Индексатор ChromaDB с поддержкой раздельных коллекций и хранилища родительских документов.
Обеспечивает детальный консольный вывод процесса индексации для PyCharm и логирование.
"""

import json
import logging
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rag_pipeline.config import (
    ALL_COLLECTIONS,
    CHROMA_DIR,
    COLLECTION_CARS,
    COLLECTION_COURT,
    COLLECTION_LAWS,
    COLLECTION_NEWS,
    COLLECTION_PDD,
    EMBEDDING_MODEL,
    ENABLE_CHROMA,
    IS_RENDER,
    LEGAL_JSONL_FILE,
    LOGS_DIR,
    MODEL_NAME,
    PDD_RULES_FILE,
)
from rag_pipeline.chunker import RAGChunker

logger = logging.getLogger("rag_indexer")
logger.setLevel(logging.INFO)

INDEXER_LOG_FILE = LOGS_DIR / "rag_indexer.log"
_ifh = logging.FileHandler(INDEXER_LOG_FILE, encoding="utf-8")
_ifh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
logger.addHandler(_ifh)


try:
    import pymorphy3
    _morph_analyzer = pymorphy3.MorphAnalyzer()
except Exception:
    _morph_analyzer = None

_LEMMA_CACHE: Dict[str, str] = {}


def lemmatize_word(word: str) -> str:
    """Нормализация слова в базовую лемму с использованием pymorphy3 и быстрым кэшированием"""
    if not _morph_analyzer:
        return word.lower()
    w_lower = word.lower()
    cached = _LEMMA_CACHE.get(w_lower)
    if cached is not None:
        return cached
    try:
        parsed = _morph_analyzer.parse(w_lower)
        normal = parsed[0].normal_form if parsed else w_lower
    except Exception:
        normal = w_lower
    if len(_LEMMA_CACHE) < 200000:
        _LEMMA_CACHE[w_lower] = normal
    return normal


def lemmatize_text(text: str) -> List[str]:
    """
    Токенизация и лемматизация текста для BM25 и гибридного поиска:
    'транспортного налога' -> ['транспортный', 'налог']
    'гражданской ответственности' -> ['гражданский', 'ответственность']
    """
    tokens = re.findall(r'\b[а-яА-Яa-zA-Z0-9_-]{2,}\b', text)
    return [lemmatize_word(t) for t in tokens]


class SimpleBM25Index:
    """
    Легковесный ин-мемори лексический индекс BM25 с морфологической лемматизацией (pymorphy3).
    Находит документы независимо от падежей, чисел и окончаний слов.
    """
    def __init__(self):
        self.corpus: List[List[str]] = []
        self.doc_ids: List[str] = []
        self.docs_map: Dict[str, Dict[str, Any]] = {}
        self.avgdl: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def tokenize(self, text: str) -> List[str]:
        return lemmatize_text(text)

    def build(self, chunks: List[Dict[str, Any]]):
        self.doc_ids = []
        self.corpus = []
        self.docs_map = {}
        self.doc_freqs = {}

        for chunk in chunks:
            c_id = chunk["id"]
            self.doc_ids.append(c_id)
            self.docs_map[c_id] = chunk
            tokens = self.tokenize(chunk["text"])
            self.corpus.append(tokens)

            for token in set(tokens):
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        n_docs = len(self.corpus)
        if n_docs > 0:
            self.avgdl = sum(len(doc) for doc in self.corpus) / n_docs
            for token, freq in self.doc_freqs.items():
                self.idf[token] = math.log(1 + (n_docs - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 20, k1: float = 1.5, b: float = 0.75) -> List[Tuple[str, float]]:
        q_tokens = self.tokenize(query)
        scores: Dict[str, float] = {}

        for idx, doc_tokens in enumerate(self.corpus):
            doc_len = len(doc_tokens)
            doc_id = self.doc_ids[idx]
            score = 0.0
            doc_token_counts = {}
            for t in doc_tokens:
                doc_token_counts[t] = doc_token_counts.get(t, 0) + 1

            for q_tok in q_tokens:
                if q_tok in doc_token_counts:
                    f = doc_token_counts[q_tok]
                    idf_val = self.idf.get(q_tok, 0.5)
                    num = f * (k1 + 1)
                    denom = f + k1 * (1 - b + b * (doc_len / (self.avgdl or 1)))
                    score += idf_val * (num / denom)

            if score > 0:
                scores[doc_id] = score

        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return sorted_items


class ChromaRAGIndexer:
    """Управление 4 коллекциями ChromaDB и родительским хранилищем с детальным логированием"""

    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self.parent_store_path = CHROMA_DIR / "parent_store.json"
        self.bm25_store_path = CHROMA_DIR / "bm25_indices.json"
        self.parent_store: Dict[str, Dict[str, Any]] = {}
        self.client = None
        self._init_client()

    def _init_client(self):
        if ENABLE_CHROMA == "false" or (ENABLE_CHROMA == "auto" and IS_RENDER):
            logger.info("Режим Render Free Tier / Low-RAM: используется легкий локальный индекс BM25 + pymorphy3.")
            self.client = None
            return
        try:
            import chromadb
            from chromadb.config import Settings
            self.client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False, is_persistent=True)
            )
            logger.info("ChromaDB PersistentClient успешно инициализирован.")
        except Exception as e:
            logger.warning(f"ChromaDB клиент не инициализирован ({e}). Будет использован локальный индекс.")
            self.client = None

    def load_parent_store(self) -> Dict[str, Dict[str, Any]]:
        if self.parent_store_path.exists():
            try:
                with open(self.parent_store_path, "r", encoding="utf-8") as f:
                    self.parent_store = json.load(f)
            except Exception:
                self.parent_store = {}
        return self.parent_store

    def save_parent_store(self):
        with open(self.parent_store_path, "w", encoding="utf-8") as f:
            json.dump(self.parent_store, f, ensure_ascii=False, indent=2)

    def index_all(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Индексация всех 4 источников:
        1. Законы ГК/НК РФ (из единого JSONL файла)
        2. Судебная практика ВС РФ (из vsrf_court_docs_rag.json)
        3. Ассортимент raskatof.ru (из cars_raskatof.json)
        4. Автоновости (из latest_autonews.json)
        """
        t_start = time.time()

        if verbose:
            print("=" * 76)
            print("🚀 RAG CHROMA ИНДЕКСАЦИЯ БАЗЫ ЗНАНИЙ (РАСКАТ АВТО РФ)")
            print("=" * 76)
            print(f"  • Время запуска:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  • Папка ChromaDB:      {CHROMA_DIR}")
            print(f"  • Модель генерации:    {MODEL_NAME}")
            print(f"  • Модель эмбеддингов:  {EMBEDDING_MODEL}")
            print(f"  • Единый файл законов: {LEGAL_JSONL_FILE}")
            print("=" * 76)

        stats = {
            "total_chunks": 0,
            "collections": {},
            "parent_docs_count": 0,
            "duration_sec": 0.0,
            "breakdown": {}
        }

        # -------------------------------------------------------------
        # ШАГ 1: Загрузка и Parent-Document чанкинг
        # -------------------------------------------------------------
        if verbose:
            print("\n[ШАГ 1/4] ИЗВЛЕЧЕНИЕ ДОКУМЕНТОВ И ИЕРАРХИЧЕСКИЙ ЧАНКИНГ (Small-to-Big)")
            print("-" * 76)

        # 1.1 Нормативная база
        t0 = time.time()
        laws_chunks, laws_parents = RAGChunker.chunk_legal_docs()
        t_laws = time.time() - t0

        tax_count = sum(1 for p in laws_parents.values() if p.get("section") == "НК РФ" or p.get("parent_id", "").startswith("tax_"))
        civics_count = sum(1 for p in laws_parents.values() if p.get("section") == "ГК РФ" or p.get("parent_id", "").startswith("civics_"))
        categories = list(set(p.get("category", "Не указана") for p in laws_parents.values()))

        if verbose:
            source_type = "JSONL (laws_gk_nk.jsonl)" if LEGAL_JSONL_FILE.exists() else ".md файлов"
            print(f"  📜 [1] Нормативная база ({source_type}):")
            print(f"     • Найдено документов:  {len(laws_parents)} шт. (НК РФ: {tax_count}, ГК РФ: {civics_count})")
            print(f"     • Категории в базе:    {', '.join(categories[:4])}{'...' if len(categories) > 4 else ''}")
            print(f"     • Сгенерировано чанков:{len(laws_chunks)} атомных пунктов (время: {t_laws:.2f} с)")

        # 1.2 Судебная практика ВС РФ
        t0 = time.time()
        court_chunks, court_parents = RAGChunker.chunk_court_docs()
        t_court = time.time() - t0
        if verbose:
            print(f"  ⚖️  [2] Судебная практика Верховного Суда РФ:")
            print(f"     • Актов ВС в базе:     {len(court_parents)} шт.")
            print(f"     • Сгенерировано чанков:{len(court_chunks)} пунктов аргументации (время: {t_court:.2f} с)")

        # 1.3 Каталог автомобилей
        t0 = time.time()
        cars_chunks, cars_parents = RAGChunker.chunk_cars_catalog()
        t_cars = time.time() - t0
        if verbose:
            print(f"  🚗 [3] Автопарк raskatof.ru:")
            print(f"     • Моделей авто:        {len(cars_parents)} шт.")
            print(f"     • Сгенерировано чанков:{len(cars_chunks)} карточек (время: {t_cars:.2f} с)")

        # 1.4 Автоновости
        t0 = time.time()
        news_chunks, news_parents = RAGChunker.chunk_auto_news()
        t_news = time.time() - t0
        if verbose:
            print(f"  📰 [4] Автоновости и рынок:")
            print(f"     • Новостных статей:    {len(news_parents)} шт.")
            print(f"     • Сгенерировано чанков:{len(news_chunks)} фрагментов (время: {t_news:.2f} с)")

        # 1.5 Правила дорожного движения РФ (ПДД РФ)
        t0 = time.time()
        pdd_chunks, pdd_parents = RAGChunker.chunk_pdd_rules()
        t_pdd = time.time() - t0
        if verbose:
            print(f"  🚦 [5] Правила дорожного движения РФ (ПДД РФ):")
            print(f"     • Смысловых пунктов:   {len(pdd_parents)} шт.")
            print(f"     • Сгенерировано чанков:{len(pdd_chunks)} пунктов/абзацев (время: {t_pdd:.2f} с)")

        # -------------------------------------------------------------
        # ШАГ 2: Сохранение объединенного хранилища Parent-документов
        # -------------------------------------------------------------
        if verbose:
            print("\n[ШАГ 2/4] СОХРАНЕНИЕ ХРАНИЛИЩА РОДИТЕЛЬСКИХ ДОКУМЕНТОВ (ParentStore)")
            print("-" * 76)

        self.parent_store.clear()
        self.parent_store.update(laws_parents)
        self.parent_store.update(court_parents)
        self.parent_store.update(cars_parents)
        self.parent_store.update(news_parents)
        self.parent_store.update(pdd_parents)
        self.save_parent_store()

        store_size_kb = round(self.parent_store_path.stat().st_size / 1024, 1) if self.parent_store_path.exists() else 0
        stats["parent_docs_count"] = len(self.parent_store)

        if verbose:
            print(f"  💾 Файл: {self.parent_store_path}")
            print(f"     • Всего родительских документов: {len(self.parent_store)} шт.")
            print(f"     • Размер на диске:               {store_size_kb} КБ")

        # -------------------------------------------------------------
        # ШАГ 3: Запись в раздельные коллекции ChromaDB
        # -------------------------------------------------------------
        if verbose:
            print("\n[ШАГ 3/4] ЗАПИСЬ В 5 РАЗДЕЛЬНЫХ КОЛЛЕКЦИЙ CHROMADB")
            print("-" * 76)

        collection_data = [
            (COLLECTION_LAWS, laws_chunks, "Нормативная база (ГК/НК РФ)"),
            (COLLECTION_COURT, court_chunks, "Судебная практика ВС РФ"),
            (COLLECTION_CARS, cars_chunks, "Каталог авто raskatof.ru"),
            (COLLECTION_NEWS, news_chunks, "Автоновости и рынок"),
            (COLLECTION_PDD, pdd_chunks, "Правила дорожного движения (ПДД РФ)")
        ]

        chroma_active = bool(self.client is not None)
        if verbose:
            mode_str = "PersistentClient (нативно на диске)" if chroma_active else "Локальный JSON-индекс (модуль chromadb не найден)"
            print(f"  Режим ChromaDB: {mode_str}")

        bm25_indices_dump = {}

        for coll_name, chunks, label in collection_data:
            c_len = len(chunks)
            if verbose:
                print(f"  • Коллекция [{coll_name}] ({label}):")

            if not chunks:
                if verbose:
                    print(f"    - Пропущено (0 чанков)")
                stats["collections"][coll_name] = 0
                continue

            # Добавляем в ChromaDB при наличии клиента
            if self.client:
                try:
                    try:
                        self.client.delete_collection(coll_name)
                    except Exception:
                        pass

                    coll = self.client.get_or_create_collection(
                        name=coll_name,
                        metadata={"hnsw:space": "cosine"}
                    )

                    ids = [c["id"] for c in chunks]
                    docs = [c["text"] for c in chunks]
                    metas = [c["metadata"] for c in chunks]

                    batch_size = 100
                    total_batches = (c_len + batch_size - 1) // batch_size
                    for b_idx in range(total_batches):
                        start = b_idx * batch_size
                        end = min(start + batch_size, c_len)
                        coll.add(
                            ids=ids[start:end],
                            documents=docs[start:end],
                            metadatas=metas[start:end]
                        )
                        if verbose:
                            pct = int((end / c_len) * 100)
                            bar = "#" * (pct // 5) + "-" * (20 - (pct // 5))
                            print(f"    - Добавлено в векторный индекс: [{bar}] {pct}% ({end}/{c_len} чанков)", end="\r")
                    if verbose:
                        print()
                except Exception as ex:
                    logger.warning(f"Ошибка записи в ChromaDB ({coll_name}): {ex}")
                    if verbose:
                        print(f"    - Ошибка ChromaDB: {ex}")

            # Подготовка данных для BM25
            bm25 = SimpleBM25Index()
            bm25.build(chunks)
            bm25_indices_dump[coll_name] = {
                "ids": [c["id"] for c in chunks],
                "texts": [c["text"] for c in chunks],
                "metas": [c["metadata"] for c in chunks],
                "avgdl": round(bm25.avgdl, 2),
                "vocab_size": len(bm25.doc_freqs)
            }

            # Сохранение резервного JSON с чанками
            chunk_backup_file = CHROMA_DIR / f"{coll_name}_chunks.json"
            with open(chunk_backup_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

            stats["collections"][coll_name] = c_len
            stats["total_chunks"] += c_len

            if verbose:
                print(f"    - Готово: {c_len} чанков проиндексировано. Словарь BM25: {len(bm25.doc_freqs)} слов.")

        # -------------------------------------------------------------
        # ШАГ 4: Сохранение BM25 поисковых индексов
        # -------------------------------------------------------------
        if verbose:
            print("\n[ШАГ 4/4] СОХРАНЕНИЕ ЛЕКСИЧЕСКИХ ИНДЕКСОВ BM25")
            print("-" * 76)

        with open(self.bm25_store_path, "w", encoding="utf-8") as f:
            json.dump(bm25_indices_dump, f, ensure_ascii=False, indent=2)

        bm25_size_kb = round(self.bm25_store_path.stat().st_size / 1024, 1) if self.bm25_store_path.exists() else 0
        if verbose:
            print(f"  💾 Файл: {self.bm25_store_path} (Размер: {bm25_size_kb} КБ)")

        # Завершение
        t_total = round(time.time() - t_start, 2)
        stats["duration_sec"] = t_total

        if verbose:
            print("\n" + "=" * 76)
            print("✅ ИНДЕКСАЦИЯ БАЗЫ ДАННЫХ RAG УСПЕШНО ЗАВЕРШЕНА!")
            print("=" * 76)
            print(f"  {'Коллекция':<22} | {'Чанков':<10} | {'Статус':<15}")
            print("  " + "-" * 55)
            for coll, count in stats["collections"].items():
                print(f"  {coll:<22} | {count:<10} | {'OK Готово':<15}")
            print("  " + "-" * 55)
            print(f"  Всего поисковых чанков:   {stats['total_chunks']}")
            print(f"  Родительских документов: {stats['parent_docs_count']}")
            print(f"  ⏱ Общее время работы:    {t_total} сек")
            print("=" * 76)

        logger.info(f"Индексация завершена: {stats['total_chunks']} чанков, {stats['parent_docs_count']} документов за {t_total} сек.")
        return stats

    def index_selected(
        self,
        target_collections: Optional[List[str]] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Быстрая выборочная переиндексация указанных коллекций.
        По умолчанию переиндексирует только легкие и часто обновляемые источники:
        Каталог автомобилей (car_catalog) и Автоновости (auto_news).
        Не затрагивает тяжелый массив нормативной базы (ГК/НК РФ) и судебной практики.
        """
        if not target_collections:
            target_collections = [COLLECTION_CARS, COLLECTION_NEWS]

        t_start = time.time()
        if verbose:
            print("=" * 76)
            print("⚡ БЫСТРАЯ ВЫБОРОЧНАЯ ПЕРЕИНДЕКСАЦИЯ RAG (АВТОПАРК + НОВОСТИ)")
            print("=" * 76)
            print(f"  • Время запуска:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  • Целевые коллекции:   {', '.join(target_collections)}")
            print("=" * 76)

        # 1. Загружаем существующий ParentStore
        self.load_parent_store()

        # 2. Загружаем существующие BM25 индексы
        bm25_store = {}
        if self.bm25_store_path.exists():
            try:
                with open(self.bm25_store_path, "r", encoding="utf-8") as f:
                    bm25_store = json.load(f)
            except Exception:
                bm25_store = {}

        stats = {
            "total_chunks": 0,
            "collections": {},
            "parent_docs_count": 0,
            "duration_sec": 0.0,
            "mode": "partial"
        }

        # 3. Выборочный чанкинг запрошенных коллекций
        chunks_map: Dict[str, Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], str]] = {}

        if COLLECTION_CARS in target_collections or "cars" in target_collections or "car_catalog" in target_collections:
            c_chunks, c_parents = RAGChunker.chunk_cars_catalog()
            chunks_map[COLLECTION_CARS] = (c_chunks, c_parents, "Каталог авто raskatof.ru")

        if COLLECTION_NEWS in target_collections or "news" in target_collections or "auto_news" in target_collections:
            n_chunks, n_parents = RAGChunker.chunk_auto_news()
            chunks_map[COLLECTION_NEWS] = (n_chunks, n_parents, "Автоновости и рынок")

        if COLLECTION_PDD in target_collections or "pdd" in target_collections or "traffic_rules" in target_collections:
            p_chunks, p_parents = RAGChunker.chunk_pdd_rules()
            chunks_map[COLLECTION_PDD] = (p_chunks, p_parents, "Правила дорожного движения (ПДД РФ)")

        if COLLECTION_COURT in target_collections or "vsrf" in target_collections or "court_cases" in target_collections:
            co_chunks, co_parents = RAGChunker.chunk_court_docs()
            chunks_map[COLLECTION_COURT] = (co_chunks, co_parents, "Судебная практика ВС РФ")

        if COLLECTION_LAWS in target_collections or "laws" in target_collections or "legal_laws" in target_collections:
            l_chunks, l_parents = RAGChunker.chunk_legal_docs()
            chunks_map[COLLECTION_LAWS] = (l_chunks, l_parents, "Нормативная база (ГК/НК РФ)")

        # 4. Обновляем ParentStore только для выбранных коллекций
        for coll_name, (chunks, parents, label) in chunks_map.items():
            self.parent_store.update(parents)
        self.save_parent_store()
        stats["parent_docs_count"] = len(self.parent_store)

        # 5. Обновляем ChromaDB и BM25
        for coll_name, (chunks, parents, label) in chunks_map.items():
            c_len = len(chunks)
            if verbose:
                print(f"  • Выборочное обновление [{coll_name}] ({label}): {c_len} чанков...")

            if self.client:
                try:
                    try:
                        self.client.delete_collection(coll_name)
                    except Exception:
                        pass

                    if chunks:
                        coll = self.client.get_or_create_collection(
                            name=coll_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                        ids = [c["id"] for c in chunks]
                        docs = [c["text"] for c in chunks]
                        metas = [c["metadata"] for c in chunks]
                        coll.add(ids=ids, documents=docs, metadatas=metas)
                except Exception as ex:
                    logger.warning(f"Ошибка выборочного обновления Chroma ({coll_name}): {ex}")

            # Обновление индекса BM25 для этой коллекции
            bm25 = SimpleBM25Index()
            bm25.build(chunks)
            bm25_store[coll_name] = {
                "ids": [c["id"] for c in chunks],
                "texts": [c["text"] for c in chunks],
                "metas": [c["metadata"] for c in chunks],
                "avgdl": round(bm25.avgdl, 2),
                "vocab_size": len(bm25.doc_freqs)
            }

            # Сохранение резервного JSON с чанками
            chunk_backup_file = CHROMA_DIR / f"{coll_name}_chunks.json"
            with open(chunk_backup_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

            stats["collections"][coll_name] = c_len
            stats["total_chunks"] += c_len

        # Сохраняем объединенный BM25 файл
        with open(self.bm25_store_path, "w", encoding="utf-8") as f:
            json.dump(bm25_store, f, ensure_ascii=False, indent=2)

        t_total = round(time.time() - t_start, 2)
        stats["duration_sec"] = t_total

        if verbose:
            print("=" * 76)
            print(f"✅ ВЫБОРОЧНАЯ ПЕРЕИНДЕКСАЦИЯ ЗАВЕРШЕНА ЗА {t_total} СЕК!")
            print(f"   Обновлено чанков: {stats['total_chunks']} (коллекции: {', '.join(chunks_map.keys())})")
            print("=" * 76)

        return stats

    index_partial = index_selected
