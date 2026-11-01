#!/usr/bin/env python3
"""
Скрипт переиндексации базы данных RAG в ChromaDB с иерархическим чанкингом.
Использование:
    python reindex_rag.py
"""

import sys
from pathlib import Path

cur_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(cur_dir))

from rag_pipeline.indexer import ChromaRAGIndexer

def main():
    print("=" * 70)
    print("🚀 ЗАПУСК ИНДЕКСАЦИИ БАЗЫ ДАННЫХ RAG В CHROMADB")
    print("=" * 70)
    print("1. Сканирование папок data/legal, data/court, data/cars, data/news...")
    print("2. Применение Parent-Document (Small-to-Big) разбиения...")
    print("3. Запись в 4 раздельные коллекции ChromaDB и создание BM25 индексов...\n")

    indexer = ChromaRAGIndexer()
    stats = indexer.index_all()

    print("\n" + "=" * 70)
    print("✅ ИНДЕКСАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
    print("=" * 70)
    print(f"Всего поисковых чанков создано:   {stats['total_chunks']}")
    print(f"Родительских документов сохранено: {stats['parent_docs_count']}")
    print("Распределение по коллекциям:")
    for coll, count in stats["collections"].items():
        print(f"  • [{coll}]: {count} чанков")
    print("=" * 70)

if __name__ == "__main__":
    main()
