#!/usr/bin/env python3
"""
Скрипт переиндексации базы данных RAG в ChromaDB с иерархическим чанкингом.
Запуск локально в PyCharm / Windows 10:
    python reindex_rag.py
"""

import sys
import traceback
from pathlib import Path

cur_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(cur_dir))

from rag_pipeline.indexer import ChromaRAGIndexer
import argparse

def main():
    parser = argparse.ArgumentParser(description="RAG ChromaDB Indexer")
    parser.add_argument(
        "--partial",
        action="store_true",
        help="Быстрая переиндексация только каталога авто и новостей (без тяжелых законов)"
    )
    parser.add_argument(
        "--collections",
        nargs="+",
        help="Список коллекций для переиндексации (например: --collections car_catalog auto_news)"
    )
    args = parser.parse_args()

    try:
        indexer = ChromaRAGIndexer()
        if args.partial or args.collections:
            target = args.collections if args.collections else ["car_catalog", "auto_news"]
            indexer.index_selected(target, verbose=True)
        else:
            indexer.index_all(verbose=True)
    except Exception as e:
        print(f"\n❌ [ОШИБКА ПЕРЕИНДЕКСАЦИИ]: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
