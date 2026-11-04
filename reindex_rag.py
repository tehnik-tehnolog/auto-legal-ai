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

def main():
    try:
        indexer = ChromaRAGIndexer()
        indexer.index_all(verbose=True)
    except Exception as e:
        print(f"\n❌ [ОШИБКА ПЕРЕИНДЕКСАЦИИ]: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
