"""
Индексатор ChromaDB с поддержкой раздельных коллекций и хранилища родительских документов.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rag_pipeline.config import (
    ALL_COLLECTIONS,
    CHROMA_DIR,
    COLLECTION_CARS,
    COLLECTION_COURT,
    COLLECTION_LAWS,
    COLLECTION_NEWS,
)
from rag_pipeline.chunker import RAGChunker

logger = logging.getLogger("rag_indexer")
logger.setLevel(logging.INFO)


class SimpleBM25Index:
    """
    Легковесный ин-мемори лексический индекс BM25 для быстрого гибридного поиска.
    Работает без тяжелых зависимостей и сохраняется на диск.
    """
    def __init__(self):
        self.corpus: List[List[str]] = []
        self.doc_ids: List[str] = []
        self.docs_map: Dict[str, Dict[str, Any]] = {}
        self.avgdl: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def tokenize(self, text: str) -> List[str]:
        import re
        tokens = re.findall(r'\b[а-яА-Яa-zA-Z0-9_-]{2,}\b', text.lower())
        return tokens

    def build(self, chunks: List[Dict[str, Any]]):
        import math
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
    """Управление 4 коллекциями ChromaDB и родительским хранилищем"""

    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self.parent_store_path = CHROMA_DIR / "parent_store.json"
        self.bm25_store_path = CHROMA_DIR / "bm25_indices.json"
        self.parent_store: Dict[str, Dict[str, Any]] = {}
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            import chromadb
            from chromadb.config import Settings
            self.client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False, is_persistent=True)
            )
        except Exception as e:
            # Если chromadb не установлен в текущем окружении, используем локальный JSON-fall-back
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

    def index_all(self) -> Dict[str, Any]:
        """
        Индексация всех 4 источников:
        1. Законы ГК/НК РФ
        2. Судебная практика ВС РФ
        3. Ассортимент raskatof.ru
        4. Автоновости
        """
        stats = {
            "total_chunks": 0,
            "collections": {},
            "parent_docs_count": 0
        }

        # 1. Извлечение чанков
        laws_chunks, laws_parents = RAGChunker.chunk_legal_docs()
        court_chunks, court_parents = RAGChunker.chunk_court_docs()
        cars_chunks, cars_parents = RAGChunker.chunk_cars_catalog()
        news_chunks, news_parents = RAGChunker.chunk_news_docs()

        # Сохранение объединенного хранилища Parent-документов
        self.parent_store.update(laws_parents)
        self.parent_store.update(court_parents)
        self.parent_store.update(cars_parents)
        self.parent_store.update(news_parents)
        self.save_parent_store()
        stats["parent_docs_count"] = len(self.parent_store)

        collection_data = [
            (COLLECTION_LAWS, laws_chunks),
            (COLLECTION_COURT, court_chunks),
            (COLLECTION_CARS, cars_chunks),
            (COLLECTION_NEWS, news_chunks)
        ]

        # Индексация в ChromaDB
        for coll_name, chunks in collection_data:
            if not chunks:
                stats["collections"][coll_name] = 0
                continue

            if self.client:
                try:
                    # Пересоздаем коллекцию
                    try:
                        self.client.delete_collection(coll_name)
                    except Exception:
                        pass

                    coll = self.client.get_or_create_collection(
                        name=coll_name,
                        metadata={"hnsw:space": "cosine"}
                    )

                    # Добавляем пачками
                    ids = [c["id"] for c in chunks]
                    docs = [c["text"] for c in chunks]
                    metas = [c["metadata"] for c in chunks]

                    batch_size = 100
                    for b_start in range(0, len(chunks), batch_size):
                        coll.add(
                            ids=ids[b_start:b_start + batch_size],
                            documents=docs[b_start:b_start + batch_size],
                            metadatas=metas[b_start:b_start + batch_size]
                        )
                except Exception as ex:
                    logger.warning(f"Ошибка записи в ChromaDB ({coll_name}): {ex}")

            # Сохранение резервной копии чанков в JSON для BM25 поиска
            chunk_backup_file = CHROMA_DIR / f"{coll_name}_chunks.json"
            with open(chunk_backup_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

            stats["collections"][coll_name] = len(chunks)
            stats["total_chunks"] += len(chunks)

        return stats
