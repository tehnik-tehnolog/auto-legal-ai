"""
RAG Pipeline Configuration.
Supports Windows, Linux, Docker, and Red Hat OpenShift (non-root container compatibility).
"""

import os
import re
import tempfile
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _is_dir_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".write_probe_{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _has_preloaded_kb(path: Path) -> bool:
    return (path / "legal" / "legal_chapters.jsonl").exists() and (path / "pdd" / "pdd_chapters.jsonl").exists()


def _resolve_data_dir(preferred: Path) -> Path:
    """
    On Red Hat OpenShift, pods run under an arbitrary non-root UID.
    Fall back to system temp directory if preferred data dir is read-only and has no preloaded KB.
    """
    if _is_dir_writable(preferred) or _has_preloaded_kb(preferred):
        return preferred
    fallback = Path(tempfile.gettempdir()) / "legal-rag-data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _resolve_writable_dir(preferred: Path, fallback_name: str) -> Path:
    if _is_dir_writable(preferred):
        return preferred
    fallback = Path(tempfile.gettempdir()) / fallback_name
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _normalize_endpoint(raw: str) -> str:
    trimmed = raw.strip().rstrip("/")
    if not trimmed:
        return ""
    if re.match(r"^https?://", trimmed, re.IGNORECASE):
        return trimmed
    return f"https://{trimmed}"


# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = _resolve_data_dir(Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data")))
CHROMA_DIR = DATA_DIR / "chroma"

LEGAL_DIR = DATA_DIR / "legal"
COURT_DIR = DATA_DIR / "court"
CARS_DIR = DATA_DIR / "cars"
NEWS_DIR = DATA_DIR / "news"
PDD_DIR = DATA_DIR / "pdd"
LOGS_DIR = _resolve_writable_dir(BASE_DIR / "logs", "legal-rag-logs")
UI_DIR = BASE_DIR / "ui"

# Paths to unified regulatory KB JSONL and structured chapter/article files
LEGAL_JSONL_FILE = LEGAL_DIR / "laws_gk_nk.jsonl"
LEGAL_CHAPTERS_FILE = LEGAL_DIR / "legal_chapters.jsonl"
PDD_RULES_FILE = PDD_DIR / "pdd_rules_rag.json"
PDD_CHAPTERS_FILE = PDD_DIR / "pdd_chapters.jsonl"
PDD_PDF_FILE = PDD_DIR / "Pravila_dorozhnogo_dvizheniya.pdf"
PDD_PDF_URL = "https://xn--b1aew.xn--p1ai/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf"

for _d in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, PDD_DIR, CHROMA_DIR]:
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

# ChromaDB collection names
COLLECTION_LAWS = "legal_laws"
COLLECTION_COURT = "court_cases"
COLLECTION_CARS = "car_catalog"
COLLECTION_NEWS = "auto_news"
COLLECTION_PDD = "traffic_rules"

ALL_COLLECTIONS = [COLLECTION_LAWS, COLLECTION_COURT, COLLECTION_CARS, COLLECTION_NEWS, COLLECTION_PDD]

# Generative model settings
MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-3.1-flash-lite-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Embedding and Cross-Encoder reranker models
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

# ChromaDB mode ('auto' | 'true' | 'false'; set ENABLE_CHROMA=false in constrained RAM pods to use BM25 + pymorphy3)
ENABLE_CHROMA = os.getenv("ENABLE_CHROMA", "auto").lower()

# Retrieval parameters
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "20"))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", "5"))
CROSS_ENCODER_TOP_N = int(os.getenv("CROSS_ENCODER_TOP_N", "25"))

# Boost factors for high-priority domain norms (leasing, vehicle rental, buyout)
PRIORITY_HIGH_BOOST = 1.35
PRIORITY_MEDIUM_BOOST = 1.15

# --- SUPABASE / POSTGRESQL CONNECTION ---
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SUPABASE_HOST = (os.getenv("HOST") or os.getenv("SUPABASE_HOST") or os.getenv("PGHOST") or "").strip()

# Note: Container platforms (including OpenShift) often inject PORT for HTTP (e.g. 8080/3000).
# Prefer explicit DB_PORT / SUPABASE_PORT / PGPORT and ignore common HTTP ports when falling back to PORT.
_raw_db_port = (
    os.getenv("DB_PORT")
    or os.getenv("SUPABASE_PORT")
    or os.getenv("PGPORT")
    or os.getenv("PORT")
    or "5432"
).strip()
if _raw_db_port in ("10000", "8501", "8080", "80", "443", "3000"):
    _raw_db_port = "6543" if "pooler" in SUPABASE_HOST else "5432"
try:
    SUPABASE_PORT = int(_raw_db_port)
except ValueError:
    SUPABASE_PORT = 6543 if "pooler" in SUPABASE_HOST else 5432

# On Linux containers USER may be set to an OS service user; only use USER when HOST is explicitly configured.
_sys_user = (os.getenv("SUPABASE_USER") or os.getenv("DB_USER") or os.getenv("PGUSER") or "").strip()
if not _sys_user and SUPABASE_HOST:
    _env_user = (os.getenv("USER") or "").strip()
    if _env_user and _env_user not in ("root", "appuser", "nobody", "default"):
        _sys_user = _env_user
SUPABASE_USER = _sys_user
SUPABASE_PASSWORD = (os.getenv("PASSWORD") or os.getenv("SUPABASE_PASSWORD") or os.getenv("PGPASSWORD") or "").strip()
SUPABASE_DBNAME = (os.getenv("DB_NAME") or os.getenv("SUPABASE_DB") or os.getenv("PGDATABASE") or "postgres").strip()

# --- BACKBLAZE B2 STORAGE (S3-COMPATIBLE) ---
B2_ENDPOINT = _normalize_endpoint(os.getenv("B2_ENDPOINT", ""))
B2_KEY_ID = (os.getenv("B2_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID") or "").strip()
B2_APPLICATION_KEY = (
    os.getenv("B2_APPLICATION_KEY")
    or os.getenv("B2_SECRET_KEY")
    or os.getenv("AWS_SECRET_ACCESS_KEY")
    or ""
).strip()
_endpoint_region_match = re.search(r"s3\.([a-z0-9-]+)\.backblazeb2\.com", B2_ENDPOINT, re.IGNORECASE)
B2_REGION = (
    os.getenv("B2_REGION")
    or (_endpoint_region_match.group(1) if _endpoint_region_match else "")
    or "eu-central-003"
).strip()
B2_BUCKET_NAME = (
    os.getenv("B2_BUCKET_NAME")
    or os.getenv("B2_BUCKET")
    or os.getenv("BACKBLAZE_BUCKET_NAME")
    or os.getenv("BACKBLAZE_BUCKET")
    or ""
).strip()
