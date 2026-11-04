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

# Единый файл нормативной базы
LEGAL_JSONL_FILE = LEGAL_DIR / "laws_gk_nk.jsonl"

# Создание необходимых директорий
for directory in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Настройки HTTP и браузера
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# API Ключи
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "pub_f09cd847b3d74c7492d4dcec897dedb6")

# Тематики НК РФ (parent_id: tax_{id}, section: "НК РФ")
CNTD_TAX_THEMES = {
    "Налог на добавленную стоимость": "https://docs.cntd.ru/federal?theme=746501331",
    "Налог на прибыль организаций": "https://docs.cntd.ru/federal?theme=746501333",
    "Налог на имущество организаций": "https://docs.cntd.ru/federal?theme=746501334",
    "Транспортный налог": "https://docs.cntd.ru/federal?theme=746501351",
    "Страховые взносы на обязательное пенсионное страхование": "https://docs.cntd.ru/federal?theme=746501350",
    "Страховые взносы в ФСС РФ на обязательное социальное страхование": "https://docs.cntd.ru/federal?theme=746501356",
    "Страховые взносы на обязательное медицинское страхование": "https://docs.cntd.ru/federal?theme=746501357",
    "Упрощенная система налогообложения": "https://docs.cntd.ru/federal?theme=746501361",
}

# Тематики ГК РФ (parent_id: civics_{id}, section: "ГК РФ")
CNTD_CIVICS_THEMES = {
    "Собственность, приватизация, арендные отношения": "https://docs.cntd.ru/federal?theme=746501320",
    "Предприятия и предпринимательская деятельность": "https://docs.cntd.ru/federal?theme=746501321",
    "Страхование и страховая деятельность": "https://docs.cntd.ru/federal?theme=746501339",
    "Несостоятельность (банкротство)": "https://docs.cntd.ru/federal?theme=746501362",
}

CNTD_THEME_URL = os.getenv("CNTD_THEME_URL", "https://docs.cntd.ru/federal?theme=746501321")
CNTD_MAX_DOCS = int(os.getenv("CNTD_MAX_DOCS", "1000"))

# Настройки для Верховного Суда РФ
VSRF_URL = "https://www.vsrf.ru/documents"
VSRF_YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
VSRF_KEYWORD = "автомобиль"

# Настройки для raskatof.ru
RASKATOF_URL = "https://raskatof.ru/"
