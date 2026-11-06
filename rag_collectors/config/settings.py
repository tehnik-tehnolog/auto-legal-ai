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
PDD_DIR = DATA_DIR / "pdd"
LOGS_DIR = BASE_DIR / "logs"

# Единый файл нормативной базы и файлы структурированных глав/статей
LEGAL_JSONL_FILE = LEGAL_DIR / "laws_gk_nk.jsonl"
LEGAL_CHAPTERS_FILE = LEGAL_DIR / "legal_chapters.jsonl"
PDD_RULES_FILE = PDD_DIR / "pdd_rules_rag.json"
PDD_CHAPTERS_FILE = PDD_DIR / "pdd_chapters.jsonl"
PDD_PDF_FILE = PDD_DIR / "Pravila_dorozhnogo_dvizheniya.pdf"
PDD_PDF_URL = "https://xn--b1aew.xn--p1ai/upload/site1000/folder_document/link/Pravila_dorozhnogo_dvizheniya.pdf"

# Создание необходимых директорий
for directory in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, PDD_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Настройки HTTP и браузера
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# API Ключи
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "pub_f09cd847b3d74c7492d4dcec897dedb6")

# Целевые нормативные акты (ГК РФ, НК РФ, КоАП РФ, законы об авто, лизинге, ОСАГО, регистрации)
# Категории сохраняют естественные пробелы (без замены на подчеркивания)
CNTD_PRIMARY_LAWS = [
    {
        "title": "ГРАЖДАНСКИЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ЧАСТЬ ПЕРВАЯ (с изменениями на 22 октября 2026 года)",
        "url": "https://docs.cntd.ru/document/9027690",
        "section": "ГК РФ",
        "category": "Гражданский кодекс РФ",
        "prefix": "civics",
        "details": "Федеральный закон от 30 ноября 1994 года № 51-ФЗ"
    },
    {
        "title": "ГРАЖДАНСКИЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ЧАСТЬ ВТОРАЯ (с изменениями на 9 июня 2026 года)",
        "url": "https://docs.cntd.ru/document/9027703",
        "section": "ГК РФ",
        "category": "Гражданский кодекс РФ",
        "prefix": "civics",
        "details": "Федеральный закон от 26 января 1996 года № 14-ФЗ (Аренда, Лизинг гл. 34)"
    },
    {
        "title": "ГРАЖДАНСКИЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ЧАСТЬ ТРЕТЬЯ (с изменениями на 8 августа 2024 года)",
        "url": "https://docs.cntd.ru/document/901799839",
        "section": "ГК РФ",
        "category": "Гражданский кодекс РФ",
        "prefix": "civics",
        "details": "Федеральный закон от 26 ноября 2001 года № 146-ФЗ"
    },
    {
        "title": "ГРАЖДАНСКИЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ЧАСТЬ ЧЕТВЕРТАЯ (с изменениями на 23 июля 2025 года)",
        "url": "https://docs.cntd.ru/document/902019731",
        "section": "ГК РФ",
        "category": "Гражданский кодекс РФ",
        "prefix": "civics",
        "details": "Федеральный закон от 18 декабря 2006 года № 230-ФЗ"
    },
    {
        "title": "РОССИЙСКАЯ ФЕДЕРАЦИЯ ФЕДЕРАЛЬНЫЙ ЗАКОН О внесении изменений в часть четвертую Гражданского кодекса Российской Федерации",
        "url": "https://docs.cntd.ru/document/1319589392",
        "section": "ГК РФ",
        "category": "Гражданский кодекс РФ",
        "prefix": "civics",
        "details": "Федеральный закон от 22 июля 2024 года № 190-ФЗ"
    },
    {
        "title": "НАЛОГОВЫЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ЧАСТЬ ПЕРВАЯ (с изменениями на 4 августа 2026 года)",
        "url": "https://docs.cntd.ru/document/901714421",
        "section": "НК РФ",
        "category": "Налоговый кодекс РФ",
        "prefix": "tax",
        "details": "Федеральный закон от 31 июля 1998 года № 146-ФЗ"
    },
    {
        "title": "НАЛОГОВЫЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ЧАСТЬ ВТОРАЯ (с изменениями на 4 августа 2026 года)",
        "url": "https://docs.cntd.ru/document/901765862",
        "section": "НК РФ",
        "category": "Налоговый кодекс РФ",
        "prefix": "tax",
        "details": "Федеральный закон от 5 августа 2000 года № 117-ФЗ (Транспортный налог гл. 28, НДС, Прибыль)"
    },
    {
        "title": "КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ОБ АДМИНИСТРАТИВНЫХ ПРАВОНАРУШЕНИЯХ (с изменениями на 4 августа 2026 года)",
        "url": "https://docs.cntd.ru/document/901807667",
        "section": "КоАП РФ",
        "category": "КоАП РФ",
        "prefix": "civics",
        "details": "Федеральный закон от 30 декабря 2001 года № 195-ФЗ (Глава 12: Нарушения в области дорожного движения)"
    },
    {
        "title": "ФЕДЕРАЛЬНЫЙ ЗАКОН Об обязательном страховании гражданской ответственности владельцев транспортных средств (с изменениями на 26 мая 2026 года)",
        "url": "https://docs.cntd.ru/document/901817083",
        "section": "Законодательство об авто и транспорте",
        "category": "ОСАГО",
        "prefix": "civics",
        "details": "Федеральный закон от 25 апреля 2002 года № 40-ФЗ"
    },
    {
        "title": "РОССИЙСКАЯ ФЕДЕРАЦИЯ ФЕДЕРАЛЬНЫЙ ЗАКОН О внесении изменений в Закон Российской Федерации \"Об организации страхового дела в Российской Федерации\" и отдельные законодательные акты Российской Федерации",
        "url": "https://docs.cntd.ru/document/420363714",
        "section": "Законодательство об авто и транспорте",
        "category": "Страховое дело",
        "prefix": "civics",
        "details": "Федеральный закон от 23 июля 2013 года № 234-ФЗ"
    },
    {
        "title": "ФЕДЕРАЛЬНЫЙ ЗАКОН О безопасности дорожного движения (с изменениями на 4 августа 2026 года)",
        "url": "https://docs.cntd.ru/document/9014765",
        "section": "Законодательство об авто и транспорте",
        "category": "Безопасность дорожного движения",
        "prefix": "civics",
        "details": "Федеральный закон от 10 декабря 1995 года № 196-ФЗ"
    },
    {
        "title": "ФЕДЕРАЛЬНЫЙ ЗАКОН О государственной регистрации транспортных средств в Российской Федерации и о внесении изменений в отдельные законодательные акты Российской Федерации (с изменениями на 4 августа 2026 года)",
        "url": "https://docs.cntd.ru/document/550835222",
        "section": "Законодательство об авто и транспорте",
        "category": "Регистрация ТС",
        "prefix": "civics",
        "details": "Федеральный закон от 3 августа 2018 года № 283-ФЗ"
    },
    {
        "title": "ЗАКОН РОССИЙСКОЙ ФЕДЕРАЦИИ О защите прав потребителей",
        "url": "https://docs.cntd.ru/document/9005388",
        "section": "Законодательство об авто и транспорте",
        "category": "Защита прав потребителей",
        "prefix": "civics",
        "details": "Закон РФ от 7 февраля 1992 года № 2300-1"
    },
    {
        "title": "ФЕДЕРАЛЬНЫЙ ЗАКОН О финансовой аренде (лизинге) (с изменениями на 28 апреля 2023 года)",
        "url": "https://docs.cntd.ru/document/901719743",
        "section": "Законодательство об авто и транспорте",
        "category": "Лизинг",
        "prefix": "civics",
        "details": "Федеральный закон от 29 октября 1998 года № 164-ФЗ"
    }
]

# Настройки для Верховного Суда РФ
VSRF_URL = "https://www.vsrf.ru/documents"
VSRF_YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
VSRF_KEYWORD = "автомобиль"

# Настройки для raskatof.ru
RASKATOF_URL = "https://raskatof.ru/"
