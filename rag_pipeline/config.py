"""
Конфигурация RAG-пайплайна для компании по раскату авто.
Поддерживает работу на Windows 10 (локальный ПК) и сервере Linux/Docker.
"""

import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Базовые директории
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))
CHROMA_DIR = DATA_DIR / "chroma"

LEGAL_DIR = DATA_DIR / "legal"
COURT_DIR = DATA_DIR / "court"
CARS_DIR = DATA_DIR / "cars"
NEWS_DIR = DATA_DIR / "news"
LOGS_DIR = BASE_DIR / "logs"

# Путь к единому файлу нормативной базы ГК РФ и НК РФ
LEGAL_JSONL_FILE = LEGAL_DIR / "laws_gk_nk.jsonl"

for _d in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, CHROMA_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# Имена коллекций в ChromaDB
COLLECTION_LAWS = "legal_laws"
COLLECTION_COURT = "court_cases"
COLLECTION_CARS = "car_catalog"
COLLECTION_NEWS = "auto_news"

ALL_COLLECTIONS = [COLLECTION_LAWS, COLLECTION_COURT, COLLECTION_CARS, COLLECTION_NEWS]

# Настройки моделей
# Выбранная пользователем модель LLM
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-3.1-flash-lite-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Модель эмбеддингов
# Поддерживает bge-m3 или text-embedding-3-large
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")

# Параметры поиска
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "20"))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", "5"))

# Коэффициент буста для высокоприоритетных норм (лизинг, аренда ТС, выкуп)
PRIORITY_HIGH_BOOST = 1.35
PRIORITY_MEDIUM_BOOST = 1.15
