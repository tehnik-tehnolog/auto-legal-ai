"""
Конфигурация RAG-пайплайна для компании по раскату авто.
Поддерживает работу на Windows 10 (локальный ПК), Linux/Docker и Render.com (Free Tier).
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
PDD_DIR = DATA_DIR / "pdd"
LOGS_DIR = BASE_DIR / "logs"
UI_DIR = BASE_DIR / "ui"

# Путь к единому файлу нормативной базы ГК РФ и НК РФ, а также структурированным главам/статьям
LEGAL_JSONL_FILE = LEGAL_DIR / "laws_gk_nk.jsonl"
LEGAL_CHAPTERS_FILE = LEGAL_DIR / "legal_chapters.jsonl"
PDD_RULES_FILE = PDD_DIR / "pdd_rules_rag.json"
PDD_CHAPTERS_FILE = PDD_DIR / "pdd_chapters.jsonl"
PDD_PDF_FILE = PDD_DIR / "Pravila_dorozhnogo_dvizheniya.pdf"
PDD_PDF_URL = "https://xn--b1aew.xn--p1ai/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf"

for _d in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, PDD_DIR, CHROMA_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# Имена коллекций в ChromaDB
COLLECTION_LAWS = "legal_laws"
COLLECTION_COURT = "court_cases"
COLLECTION_CARS = "car_catalog"
COLLECTION_NEWS = "auto_news"
COLLECTION_PDD = "traffic_rules"

ALL_COLLECTIONS = [COLLECTION_LAWS, COLLECTION_COURT, COLLECTION_CARS, COLLECTION_NEWS, COLLECTION_PDD]

# Настройки моделей
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-3.1-flash-lite-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Модель эмбеддингов
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")

# Режим ChromaDB (на Render Free Tier 512MB RAM по умолчанию используется легкий BM25+pymorphy3 если ENABLE_CHROMA=auto)
IS_RENDER = os.getenv("RENDER", "").lower() == "true" or bool(os.getenv("RENDER_SERVICE_ID"))
ENABLE_CHROMA = os.getenv("ENABLE_CHROMA", "auto").lower()

# Параметры поиска
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "20"))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", "5"))

# Коэффициент буста для высокоприоритетных норм (лизинг, аренда ТС, выкуп)
PRIORITY_HIGH_BOOST = 1.35
PRIORITY_MEDIUM_BOOST = 1.15

# --- SUPABASE / POSTGRESQL CONNECTION ---
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SUPABASE_HOST = (os.getenv("HOST") or os.getenv("SUPABASE_HOST") or os.getenv("PGHOST") or "").strip()

# Примечание: Render.com перезаписывает системный PORT значением веб-порта (например 10000).
# Поэтому приоритетно читаем DB_PORT / SUPABASE_PORT / PGPORT, а PORT используем только если он валидный порт БД.
_raw_db_port = (
    os.getenv("DB_PORT")
    or os.getenv("SUPABASE_PORT")
    or os.getenv("PGPORT")
    or os.getenv("PORT")
    or "5432"
).strip()
if _raw_db_port in ("10000", "8501", "80", "443", "3000"):
    _raw_db_port = "6543" if "pooler" in SUPABASE_HOST else "5432"
try:
    SUPABASE_PORT = int(_raw_db_port)
except ValueError:
    SUPABASE_PORT = 6543 if "pooler" in SUPABASE_HOST else 5432

# На Linux USER может быть равен 'root' или 'appuser' в системе — берем USER только при настроенном HOST и PASSWORD
_sys_user = (os.getenv("SUPABASE_USER") or os.getenv("DB_USER") or os.getenv("PGUSER") or "").strip()
if not _sys_user and SUPABASE_HOST:
    _env_user = (os.getenv("USER") or "").strip()
    if _env_user and _env_user not in ("root", "appuser", "nobody", "render"):
        _sys_user = _env_user
SUPABASE_USER = _sys_user
SUPABASE_PASSWORD = (os.getenv("PASSWORD") or os.getenv("SUPABASE_PASSWORD") or os.getenv("PGPASSWORD") or "").strip()
SUPABASE_DBNAME = (os.getenv("DB_NAME") or os.getenv("SUPABASE_DB") or os.getenv("PGDATABASE") or "postgres").strip()

# --- BACKBLAZE B2 STORAGE (S3-COMPATIBLE) ---
B2_ENDPOINT = os.getenv("B2_ENDPOINT", "").strip()
B2_KEY_ID = os.getenv("B2_KEY_ID", "").strip()
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY", "").strip()
B2_REGION = os.getenv("B2_REGION", "eu-central-003").strip()
B2_BUCKET_NAME = (os.getenv("B2_BUCKET_NAME") or os.getenv("B2_BUCKET") or "").strip()

# --- RENDER WAKE-UP WEBHOOK URL ---
WEBHOOK_BASE_URL = (
    os.getenv("WEBHOOK_BASE_URL")
    or os.getenv("RENDER_EXTERNAL_URL")
    or os.getenv("APP_URL")
    or ""
).strip().rstrip("/")
