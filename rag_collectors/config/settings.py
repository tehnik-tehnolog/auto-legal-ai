import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Базовые директории
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent if (BASE_DIR.parent / "streamlit_app.py").exists() else BASE_DIR
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", PROJECT_ROOT / "data"))

# Поддиректории для каждого источника данных
LEGAL_DIR = DATA_DIR / "legal"
COURT_DIR = DATA_DIR / "court"
CARS_DIR = DATA_DIR / "cars"
NEWS_DIR = DATA_DIR / "news"
LOGS_DIR = BASE_DIR / "logs"

# Создание необходимых директорий
for directory in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Настройки HTTP и браузера
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# API Ключи
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "pub_f09cd847b3d74c7492d4dcec897dedb6")

# Настройки дляdocs.cntd.ru (ГК РФ / НК РФ)
CNTD_THEME_URL = os.getenv("CNTD_THEME_URL", "https://docs.cntd.ru/federal?theme=746501321")
CNTD_MAX_DOCS = int(os.getenv("CNTD_MAX_DOCS", "1000"))

# Настройки для Верховного Суда РФ
VSRF_URL = "https://www.vsrf.ru/documents"
VSRF_YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
VSRF_KEYWORD = "автомобиль"

# Настройки для raskatof.ru
RASKATOF_URL = "https://raskatof.ru/"
