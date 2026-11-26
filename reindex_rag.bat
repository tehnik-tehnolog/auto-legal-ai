@echo off
:: ==============================================================================
:: Re-index the RAG knowledge base (ChromaDB + BM25) from local data/
:: ==============================================================================
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe reindex_rag.py
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe reindex_rag.py
) else (
    python reindex_rag.py
)
pause
