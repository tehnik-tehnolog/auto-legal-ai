@echo off
:: ==============================================================================
:: Переиндексация базы RAG в ChromaDB на Windows 10
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
