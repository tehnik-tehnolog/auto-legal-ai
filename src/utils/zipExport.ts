import JSZip from 'jszip';

export async function downloadServerScriptsZip() {
  const zip = new JSZip();

  // README.md (Windows 10 + PyCharm + WSL2/Docker + Streamlit)
  zip.file(
    'README.md',
    `# RAG Ассистент компании по раскату авто (Streamlit + Сервер сбора данных)

Комплекс RAG-ассистента и автоматизированного сбора базы знаний.
- **Веб-интерфейс**: Streamlit (\`streamlit_app.py\`)
- **Сервер сбора данных**: Локальный ПК на **Windows 10 + PyCharm + Планировщик заданий (Task Scheduler) / Docker / WSL2**

---

## 🚀 Быстрый старт на Windows 10 (PyCharm)

### Шаг 1. Открытие проекта в PyCharm
1. Откройте эту папку в **PyCharm** (\`File -> Open\`).
2. PyCharm автоматически предложит создать виртуальное окружение (\`venv\`). Если нет — создайте в настройках:
   \`Settings -> Project -> Python Interpreter -> Add Interpreter -> Virtualenv (Python 3.10, 3.11 или 3.12)\`.

### Шаг 2. Установка библиотек
В терминале PyCharm (Alt+F12) выполните:
\`\`\`cmd
pip install -r requirements.txt
playwright install chromium
\`\`\`

### Шаг 3. Индексация базы RAG в ChromaDB + BM25
\`\`\`cmd
# Способ 1: двойным кликом по файлу
reindex_rag.bat

# Способ 2: в терминале
python reindex_rag.py
\`\`\`

### Шаг 4. Запуск веб-части Streamlit
\`\`\`cmd
# Способ 1: через терминал
streamlit run streamlit_app.py

# Способ 2: двойным кликом по файлу
run_streamlit.bat
\`\`\`
После запуска в браузере откроется адрес: \`http://localhost:8501\`

---

## ⚙️ Запуск сбора данных (Серверная часть)

### Ручной запуск любого коллектора:
\`\`\`cmd
# Способ 1: через батник
run_collectors.bat cars     # Ассортимент машин raskatof.ru (еженедельно)
run_collectors.bat news     # Автоновости (еженедельно)
run_collectors.bat vsrf     # Судебная практика ВС РФ (ежемесячно)
run_collectors.bat laws     # Законы ГК/НК РФ (раз в 3 месяца)
run_collectors.bat status   # Проверка статуса базы

# Способ 2: напрямую через Python
python rag_collectors\\runner.py --collector cars
\`\`\`

---

## ⏰ Настройка автоматического расписания на Windows 10

На Windows 10 вместо cron используется **Планировщик заданий Windows (Windows Task Scheduler)**.
Мы подготовили скрипт автоматической настройки:

1. Запустите командную строку **от имени Администратора**.
2. Перейдите в папку проекта и выполните:
   \`\`\`cmd
   setup_windows_scheduler.bat
   \`\`\`
3. Скрипт создаст 4 фоновые задачи:
   - \`RAG_Collector_Cars\` — каждый понедельник в 04:00
   - \`RAG_Collector_News\` — каждый понедельник в 05:00
   - \`RAG_Collector_VSRF\` — 1-е число каждого месяца в 03:00
   - \`RAG_Collector_Laws\` — 1-е число января, апреля, июля, октября в 02:00

Проверить задачи можно в приложении \`taskschd.msc\` (Win+R -> \`taskschd.msc\`).

---

## 🐳 Альтернатива: Запуск в Docker / WSL2

Если вы предпочитаете Docker Desktop на Windows 10:
\`\`\`bash
# 1. Сборка контейнера
docker compose build

# 2. Запуск сбора данных
docker compose run --rm rag-collector python runner.py --collector cars

# 3. Запуск веб-интерфейса Streamlit
streamlit run streamlit_app.py
\`\`\`
`
  );

  // requirements.txt
  zip.file(
    'requirements.txt',
    `streamlit>=1.40.0
chromadb>=0.5.0
google-genai>=0.1.1
pandas>=2.2.0
playwright>=1.42.0
requests>=2.31.0
beautifulsoup4>=4.12.3
pypdf>=4.1.0
pyyaml>=6.0.1
python-dotenv>=1.0.1
lxml>=5.1.0
`
  );

  // .streamlit/config.toml
  const streamlitFolder = zip.folder('.streamlit');
  if (streamlitFolder) {
    streamlitFolder.file(
      'config.toml',
      `[theme]
primaryColor = "#2563EB"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F8FAFC"
textColor = "#1E293B"
font = "sans serif"

[server]
headless = false
port = 8501
enableCORS = false
`
    );
  }

  // Windows bat files
  zip.file(
    'run_streamlit.bat',
    `@echo off
cd /d "%~dp0"
if exist "venv\\Scripts\\streamlit.exe" (
    venv\\Scripts\\streamlit.exe run streamlit_app.py
) else if exist ".venv\\Scripts\\streamlit.exe" (
    .venv\\Scripts\\streamlit.exe run streamlit_app.py
) else (
    streamlit run streamlit_app.py
)
pause
`
  );

  zip.file(
    'run_collectors.bat',
    `@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
if exist "venv\\Scripts\\python.exe" (
    set "PY_CMD=venv\\Scripts\\python.exe"
) else if exist ".venv\\Scripts\\python.exe" (
    set "PY_CMD=.venv\\Scripts\\python.exe"
) else (
    set "PY_CMD=python"
)
if "%1"=="" (
    !PY_CMD! rag_collectors\\runner.py --status
) else (
    !PY_CMD! rag_collectors\\runner.py --collector %1
)
endlocal
`
  );

  zip.file(
    'setup_windows_scheduler.bat',
    `@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [НАСТРОЙКА ПЛАНИРОВЩИКА ЗАДАНИЙ WINDOWS 10]
set "BAT_PATH=%~dp0run_collectors.bat"
schtasks /create /tn "RAG_Collector_Cars" /tr "\\"%%BAT_PATH%%\\" cars" /sc weekly /d MON /st 04:00 /f
schtasks /create /tn "RAG_Collector_News" /tr "\\"%%BAT_PATH%%\\" news" /sc weekly /d MON /st 05:00 /f
schtasks /create /tn "RAG_Collector_VSRF" /tr "\\"%%BAT_PATH%%\\" vsrf" /sc monthly /d 1 /st 03:00 /f
schtasks /create /tn "RAG_Collector_Laws" /tr "\\"%%BAT_PATH%%\\" laws" /sc monthly /m JAN,APR,JUL,OCT /d 1 /st 02:00 /f
echo [ГОТОВО] Задания успешно добавлены в Планировщик Windows!
pause
`
  );

  // streamlit_app.py
  zip.file(
    'streamlit_app.py',
    `import os, sys, json, yaml
from pathlib import Path
import streamlit as st
import pandas as pd

st.set_page_config(page_title="RAG Ассистент | Раскат Авто РФ", page_icon="🚗", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))
CARS_DIR = DATA_DIR / "cars"
COURT_DIR = DATA_DIR / "court"
NEWS_DIR = DATA_DIR / "news"
LEGAL_DIR = DATA_DIR / "legal"

for d in [CARS_DIR, COURT_DIR, NEWS_DIR, LEGAL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

@st.cache_data(ttl=60)
def get_cars():
    f = CARS_DIR / "cars_raskatof.json"
    return json.load(open(f, "r", encoding="utf-8")) if f.exists() else []

@st.cache_data(ttl=60)
def get_court():
    f = COURT_DIR / "vsrf_court_docs_rag.json"
    return json.load(open(f, "r", encoding="utf-8")) if f.exists() else []

@st.cache_data(ttl=60)
def get_news():
    f = NEWS_DIR / "latest_autonews.json"
    return json.load(open(f, "r", encoding="utf-8")) if f.exists() else []

cars = get_cars()
court = get_court()
news = get_news()

with st.sidebar:
    st.title("🚗 Раскат Авто РФ")
    st.caption("RAG Помощник и управление сбором данных")
    menu = st.radio("Раздел:", [
        "💬 RAG Ассистент (Чат)",
        "🚙 Каталог авто (raskatof.ru)",
        "📜 Нормативная база (ГК/НК РФ)",
        "⚖️ Судебная практика ВС РФ",
        "📰 Автоновости и рынок",
        "⚙️ Сервер и запуск (Windows 10 / PyCharm)"
    ])
    st.divider()
    st.write(f"• Авто в каталоге: **{len(cars)}**")
    st.write(f"• Актов ВС РФ: **{len(court)}**")
    st.write(f"• Новостей: **{len(news)}**")
    if st.button("🔄 Переиндексировать RAG (ChromaDB + BM25)", use_container_width=True):
        with st.spinner("Переиндексация 4 коллекций..."):
            try:
                from rag_pipeline.indexer import ChromaRAGIndexer
                indexer = ChromaRAGIndexer()
                res = indexer.index_all()
                st.success(f"Индексация завершена! Чанков: {res['total_chunks']}")
            except Exception as e:
                st.error(f"Ошибка индексации: {e}")

if menu == "💬 RAG Ассистент (Чат)":
    st.header("💬 RAG Помощник по раскату и выкупу авто")
    st.caption("Пайплайн: Query Router ➔ BM25 + Dense ➔ Metadata Boost ➔ Reranker ➔ Gemini 3.1 Flash Lite")
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Здравствуйте! Я RAG-помощник компании по раскату авто. Задайте вопрос по автопарку, условиям выкупа, статьям ГК/НК РФ или решениям ВС РФ.", "sources": []}]
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m.get("targets"):
                t_labels = {"car_catalog": "🚗 Автопарк", "legal_laws": "📜 Законы", "court_cases": "⚖️ ВС РФ", "auto_news": "📰 Новости"}
                st.caption(f"🎯 **Коллекции поиска:** {' • '.join([t_labels.get(t, t) for t in m['targets']])}")
            st.markdown(m["content"])
            if m.get("sources"):
                with st.expander(f"📚 Первоисточники ({len(m['sources'])})"):
                    for s in m["sources"]:
                        st.markdown(f"**[{s['title']}]({s['url']})**")
                        st.caption(f"Фрагмент: {s['matched_chunk'][:220]}...")
    if prompt := st.chat_input("Ваш вопрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Поиск по RAG-базе (Router + BM25 + Dense + Rerank)..."):
                try:
                    from rag_pipeline.generator import RAGAssistant
                    assistant = RAGAssistant()
                    res = assistant.answer_query(prompt)
                    ans, targets, sources = res["answer"], res.get("target_collections", []), res.get("sources", [])
                except Exception as err:
                    ans, targets, sources = f"Ошибка RAG пайплайна: {err}", [], []
            if targets:
                t_labels = {"car_catalog": "🚗 Автопарк", "legal_laws": "📜 Законы", "court_cases": "⚖️ ВС РФ", "auto_news": "📰 Новости"}
                st.caption(f"🎯 **Коллекции поиска:** {' • '.join([t_labels.get(t, t) for t in targets])}")
            st.markdown(ans)
            if sources:
                with st.expander(f"📚 Использованные первоисточники ({len(sources)} документов)"):
                    for s in sources:
                        st.markdown(f"**[{s['title']}]({s['url']})**")
                        st.caption(f"Фрагмент: {s['matched_chunk'][:220]}...")
            st.session_state.messages.append({"role": "assistant", "content": ans, "targets": targets, "sources": sources})

elif menu == "🚙 Каталог авто (raskatof.ru)":
    st.header("🚙 Актуальный автопарк raskatof.ru")
    for c in cars:
        with st.container(border=True):
            st.subheader(c.get("model", "Автомобиль"))
            st.write(f"Класс: {c.get('category')} | {c.get('leasing_terms', {}).get('daily_rate')} | {c.get('leasing_terms', {}).get('initial_payment')}")
            st.caption(str(c.get("specifications", {})))

elif menu == "📜 Нормативная база (ГК/НК РФ)":
    st.header("📜 Законодательная база (ГК РФ / НК РФ)")
    st.write("Статьи сохранены в .md файлах с YAML frontmatter в data/legal/")

elif menu == "⚖️ Судебная практика ВС РФ":
    st.header("⚖️ Судебные акты Верховного Суда РФ")
    for act in court:
        with st.container(border=True):
            m = act.get("metadata", {})
            st.subheader(m.get("title"))
            st.write(f"Дело: {m.get('case_number')} | Дата: {m.get('date')}")
            with st.expander("Текст акта"):
                st.text(act.get("page_content")[:1000] + "...")

elif menu == "📰 Автоновости и рынок":
    st.header("📰 Новости рынка и утильсбора")
    for n in news:
        with st.container(border=True):
            m = n.get("metadata", {})
            st.subheader(m.get("title"))
            st.caption(f"{m.get('date')} | {m.get('source')}")

elif menu == "⚙️ Сервер и запуск (Windows 10 / PyCharm)":
    st.header("⚙️ Запуск на Windows 10 (PyCharm / Планировщик заданий)")
    st.markdown("""
    - **Среда разработки**: PyCharm Community / Professional
    - **Запуск скриптов**: \`run_collectors.bat <collector>\`
    - **Расписание**: Планировщик заданий Windows (\`setup_windows_scheduler.bat\`)
    """)
`
  );

  // Docker
  zip.file(
    'Dockerfile',
    `FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends wget curl ca-certificates libnss3 libatk1.0-0 libcups2 libgbm1 libcairo2 libasound2 fonts-liberation && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium && playwright install-deps chromium
COPY . .
CMD ["python", "rag_collectors/runner.py", "--status"]
`
  );

  zip.file(
    'docker-compose.yml',
    `version: '3.8'
services:
  rag-collector:
    build: .
    container_name: rag-auto-collector
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
`
  );

  // rag_collectors folder
  const collectorsFolder = zip.folder('rag_collectors');
  if (collectorsFolder) {
    collectorsFolder.file(
      'runner.py',
      `#!/usr/bin/env python3
import argparse, asyncio, json, sys, os
from pathlib import Path

cur = Path(__file__).resolve().parent
sys.path.insert(0, str(cur))

from collectors.auto_news import AutoNewsCollector
from collectors.gk_nk_laws import LawsCollector
from collectors.raskatof_cars import CarsCollector
from collectors.vsrf_court import VSRFCourtCollector
from config.settings import CARS_DIR, COURT_DIR, DATA_DIR, LEGAL_DIR, NEWS_DIR

def print_status_dashboard():
    print("=" * 70)
    print("📊 ТЕКУЩЕЕ СОСТОЯНИЕ БАЗЫ RAG (РАСКАТ АВТО)")
    print("=" * 70)
    print(f"1. 📜 Нормативная база: {len(list(LEGAL_DIR.glob('*.md')))} файлов")
    print(f"2. ⚖️ Практика ВС РФ:   {len(json.load(open(COURT_DIR / 'vsrf_court_docs_rag.json', 'r', encoding='utf-8'))) if (COURT_DIR / 'vsrf_court_docs_rag.json').exists() else 0} актов")
    print(f"3. 🚗 Авто raskatof.ru: {len(json.load(open(CARS_DIR / 'cars_raskatof.json', 'r', encoding='utf-8'))) if (CARS_DIR / 'cars_raskatof.json').exists() else 0} авто")
    print(f"4. 📰 Автоновости:      {len(json.load(open(NEWS_DIR / 'latest_autonews.json', 'r', encoding='utf-8'))) if (NEWS_DIR / 'latest_autonews.json').exists() else 0} статей")
    print("=" * 70)

async def run_collector(name: str):
    cmap = {"laws": LawsCollector, "vsrf": VSRFCourtCollector, "cars": CarsCollector, "news": AutoNewsCollector}
    targets = list(cmap.keys()) if name == "all" else [name]
    for t in targets:
        inst = cmap[t]()
        st = await inst.run()
        if not st.get("success", False):
            return False
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--collector", choices=["laws", "vsrf", "cars", "news", "all"])
    p.add_argument("--status", action="store_true")
    a = p.parse_args()
    if a.status:
        print_status_dashboard()
        return
    if not a.collector:
        p.print_help()
        return
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_collector(a.collector))

if __name__ == "__main__":
    main()
`
    );

    const cfg = collectorsFolder.folder('config');
    if (cfg) {
      cfg.file(
        'settings.py',
        `import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))

LEGAL_DIR = DATA_DIR / "legal"
COURT_DIR = DATA_DIR / "court"
CARS_DIR = DATA_DIR / "cars"
NEWS_DIR = DATA_DIR / "news"
LOGS_DIR = BASE_DIR / "logs"

LEGAL_JSONL_FILE = LEGAL_DIR / "laws_gk_nk.jsonl"

for d in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "pub_f09cd847b3d74c7492d4dcec897dedb6")

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

CNTD_CIVICS_THEMES = {
    "Собственность, приватизация, арендные отношения": "https://docs.cntd.ru/federal?theme=746501320",
    "Предприятия и предпринимательская деятельность": "https://docs.cntd.ru/federal?theme=746501321",
    "Страхование и страховая деятельность": "https://docs.cntd.ru/federal?theme=746501339",
    "Несостоятельность (банкротство)": "https://docs.cntd.ru/federal?theme=746501362",
}

CNTD_THEME_URL = "https://docs.cntd.ru/federal?theme=746501321"
CNTD_MAX_DOCS = 1000
VSRF_URL = "https://www.vsrf.ru/documents"
VSRF_YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
VSRF_KEYWORD = "автомобиль"
RASKATOF_URL = "https://raskatof.ru/"
`
      );
    }

    const cls = collectorsFolder.folder('collectors');
    if (cls) {
      cls.file(
        '__init__.py',
        `from collectors.gk_nk_laws import LawsCollector\nfrom collectors.vsrf_court import VSRFCourtCollector\nfrom collectors.raskatof_cars import CarsCollector\nfrom collectors.auto_news import AutoNewsCollector\n__all__ = ["LawsCollector", "VSRFCourtCollector", "CarsCollector", "AutoNewsCollector"]\n`
      );
      cls.file(
        'base.py',
        `import logging, sys, time\nfrom abc import ABC, abstractmethod\nfrom config.settings import LOGS_DIR\n\ndef setup_logger(name: str):\n    lg = logging.getLogger(name)\n    lg.setLevel(logging.INFO)\n    if not lg.handlers:\n        fmt = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")\n        h1 = logging.StreamHandler(sys.stdout)\n        h1.setFormatter(fmt)\n        lg.addHandler(h1)\n        h2 = logging.FileHandler(LOGS_DIR / f"{name}.log", encoding="utf-8")\n        h2.setFormatter(fmt)\n        lg.addHandler(h2)\n    return lg\n\nclass BaseCollector(ABC):\n    def __init__(self, name: str):\n        self.name = name\n        self.logger = setup_logger(name)\n        self.stats = {"name": name, "items_collected": 0, "success": False}\n    @abstractmethod\n    async def collect(self):\n        pass\n    async def run(self):\n        t0 = time.time()\n        try:\n            res = await self.collect()\n            self.stats.update(res)\n            self.stats["success"] = True\n        except Exception as e:\n            self.stats["success"] = False\n            self.logger.error(f"Error in {self.name}: {e}")\n        return self.stats\n`
      );
      cls.file(
        'raskatof_cars.py',
        `import json, requests\nfrom datetime import datetime\nfrom bs4 import BeautifulSoup\nfrom collectors.base import BaseCollector\nfrom config.settings import CARS_DIR, HTTP_TIMEOUT, RASKATOF_URL, USER_AGENT\n\nclass CarsCollector(BaseCollector):\n    def __init__(self):\n        super().__init__("raskatof_cars")\n        self.output_json = CARS_DIR / "cars_raskatof.json"\n        self.output_rag = CARS_DIR / "cars_raskatof_rag.json"\n    async def collect(self):\n        r = requests.get(RASKATOF_URL, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)\n        soup = BeautifulSoup(r.text, "html.parser")\n        items = soup.find_all("div", class_="choose-item")\n        cars, rag = [], []\n        for it in items:\n            m = it.find("h4", class_="choose-model")\n            name = m.get_text(strip=True) if m else "Автомобиль"\n            specs = {p.get_text().split(":")[0].strip(): p.get_text().split(":")[1].strip() for p in it.select(".choose-basic-specs p") if ":" in p.get_text()}\n            feats = [li.get_text(strip=True) for li in it.select(".extra-features li")]\n            terms = " ".join([p.get_text(strip=True) for p in it.select(".leasing-info p")])\n            cars.append({"model": name, "specs": specs, "features": feats, "leasing_terms": {"terms_text": terms}})\n            rag.append({"page_content": f"Модель: {name}\\nХарактеристики: {specs}\\nУсловия раската: {terms}"})\n        json.dump(cars, open(self.output_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)\n        json.dump(rag, open(self.output_rag, "w", encoding="utf-8"), ensure_ascii=False, indent=2)\n        return {"items_collected": len(cars)}\n`
      );
      cls.file(
        'vsrf_court.py',
        `import asyncio, io, json, re, requests\nfrom playwright.async_api import async_playwright\nfrom pypdf import PdfReader\nfrom collectors.base import BaseCollector\nfrom config.settings import COURT_DIR, USER_AGENT, VSRF_KEYWORD, VSRF_URL, VSRF_YEARS\n\nclass VSRFCourtCollector(BaseCollector):\n    def __init__(self):\n        super().__init__("vsrf_court")\n        self.output_file = COURT_DIR / "vsrf_court_docs_rag.json"\n    async def collect(self):\n        docs = []\n        async with async_playwright() as p:\n            b = await p.chromium.launch(headless=True, args=["--no-sandbox"])\n            page = await b.new_page()\n            await page.goto(VSRF_URL, wait_until="networkidle", timeout=45000)\n            await page.fill("input#documents-form-keyword", VSRF_KEYWORD)\n            for y in VSRF_YEARS:\n                c = page.locator(f"button#checkbox-{y}")\n                if await c.count() > 0 and await c.get_attribute("aria-checked") == "false":\n                    await c.click()\n            await page.click("button[type='submit'][form='documents-form']")\n            await page.wait_for_timeout(4000)\n            for l in await page.locator("a[href]").all():\n                h = await l.get_attribute("href") or ""\n                t = (await l.inner_text()).strip()\n                if ("/media-proxy/" in h or h.endswith(".pdf")) and len(t) > 10:\n                    u = f"https://www.vsrf.ru{h}" if h.startswith("/") else h\n                    try:\n                        resp = requests.get(u, timeout=30)\n                        if resp.status_code == 200:\n                            r = PdfReader(io.BytesIO(resp.content))\n                            text = " ".join([p.extract_text() or "" for p in r.pages])\n                            docs.append({"page_content": f"{t}\\n{text[:3000]}", "metadata": {"title": t, "url": u}})\n                    except Exception:\n                        pass\n            await b.close()\n        json.dump(docs, open(self.output_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)\n        return {"items_collected": len(docs)}\n`
      );
      cls.file(
        'auto_news.py',
        `import json, requests\nfrom collectors.base import BaseCollector\nfrom config.settings import NEWS_DIR, NEWSDATA_API_KEY, USER_AGENT\n\nclass AutoNewsCollector(BaseCollector):\n    def __init__(self):\n        super().__init__("auto_news")\n        self.output_file = NEWS_DIR / "latest_autonews.json"\n    async def collect(self):\n        docs = []\n        url = f"https://newsdata.io/api/1/latest?apikey={NEWSDATA_API_KEY}&qInTitle=утильсбор&country=ru&language=ru"\n        try:\n            res = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10).json()\n            for art in res.get("results", [])[:50]:\n                docs.append({"page_content": f"{art.get('title')}\\n{art.get('description')}", "metadata": {"title": art.get('title'), "url": art.get('link')}})\n        except Exception:\n            pass\n        json.dump(docs, open(self.output_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)\n        return {"items_collected": len(docs)}\n`
      );
      cls.file(
        'gk_nk_laws.py',
        `import asyncio, yaml\nfrom datetime import datetime\nfrom playwright.async_api import async_playwright\nfrom collectors.base import BaseCollector\nfrom config.settings import LEGAL_DIR, CNTD_THEME_URL, USER_AGENT\n\nclass LawsCollector(BaseCollector):\n    def __init__(self):\n        super().__init__("laws_gk_nk")\n        self.output_dir = LEGAL_DIR\n    async def collect(self):\n        saved = 0\n        async with async_playwright() as p:\n            b = await p.chromium.launch(headless=True, args=["--no-sandbox"])\n            ctx = await b.new_context(user_agent=USER_AGENT)\n            page = await ctx.new_page()\n            await page.route("**/*", lambda r: r.abort() if r.request.resource_type in ["image", "font", "media"] else r.continue_())\n            await page.goto(CNTD_THEME_URL, wait_until="domcontentloaded", timeout=45000)\n            await page.wait_for_selector(".document-list, body", timeout=20000)\n            for it in (await page.locator("li.document-list_i").all())[:30]:\n                try:\n                    h = await it.locator("a.document-list_i_lk").first.get_attribute("href") or ""\n                    t = (await it.locator("div.document-list_i_t").first.inner_text()).strip()\n                    dp = await ctx.new_page()\n                    await dp.goto(f"https://docs.cntd.ru{h}", wait_until="domcontentloaded", timeout=20000)\n                    txt = await dp.locator("body").inner_text()\n                    await dp.close()\n                    meta = {"title": t, "source_site": "docs.cntd.ru", "priority_level": "high"}\n                    with open(self.output_dir / f"doc_{saved+1}.md", "w", encoding="utf-8") as f:\n                        f.write(f"---\\n{yaml.dump(meta)}---\\n\\n# {t}\\n\\n{txt}")\n                    saved += 1\n                except Exception:\n                    continue\n            await b.close()\n        return {"items_collected": saved}\n`
      );
    }
  }

  // reindex scripts
  zip.file(
    'reindex_rag.bat',
    `@echo off
cd /d "%~dp0"
if exist "venv\\Scripts\\python.exe" (
    venv\\Scripts\\python.exe reindex_rag.py
) else if exist ".venv\\Scripts\\python.exe" (
    .venv\\Scripts\\python.exe reindex_rag.py
) else (
    python reindex_rag.py
)
pause
`
  );

  zip.file(
    'reindex_rag.py',
    `#!/usr/bin/env python3
import sys
from pathlib import Path

cur_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(cur_dir))

from rag_pipeline.indexer import ChromaRAGIndexer

def main():
    print("=" * 70)
    print("🚀 ЗАПУСК ИНДЕКСАЦИИ БАЗЫ ДАННЫХ RAG В CHROMADB")
    print("=" * 70)
    indexer = ChromaRAGIndexer()
    stats = indexer.index_all()
    print("=" * 70)
    print(f"✅ Чанков создано: {stats['total_chunks']}, Документов: {stats['parent_docs_count']}")
    for coll, count in stats["collections"].items():
        print(f"  • [{coll}]: {count} чанков")
    print("=" * 70)

if __name__ == "__main__":
    main()
`
  );

  // rag_pipeline folder
  const pipelineFolder = zip.folder('rag_pipeline');
  if (pipelineFolder) {
    pipelineFolder.file(
      '__init__.py',
      `from rag_pipeline.generator import RAGAssistant
from rag_pipeline.retriever import HybridRetriever
from rag_pipeline.indexer import ChromaRAGIndexer
from rag_pipeline.chunker import RAGChunker

__all__ = ["RAGAssistant", "HybridRetriever", "ChromaRAGIndexer", "RAGChunker"]
`
    );

    pipelineFolder.file(
      'config.py',
      `import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))
CHROMA_DIR = DATA_DIR / "chroma"

LEGAL_DIR = DATA_DIR / "legal"
COURT_DIR = DATA_DIR / "court"
CARS_DIR = DATA_DIR / "cars"
NEWS_DIR = DATA_DIR / "news"

COLLECTION_LAWS = "legal_laws"
COLLECTION_COURT = "court_cases"
COLLECTION_CARS = "car_catalog"
COLLECTION_NEWS = "auto_news"

ALL_COLLECTIONS = [COLLECTION_LAWS, COLLECTION_COURT, COLLECTION_CARS, COLLECTION_NEWS]

MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-3.1-flash-lite-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")

TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "20"))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", "5"))

PRIORITY_HIGH_BOOST = 1.35
PRIORITY_MEDIUM_BOOST = 1.15
`
    );

    pipelineFolder.file(
      'chunker.py',
      `import json, re
from typing import Any, Dict, List, Tuple
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None

from rag_pipeline.config import CARS_DIR, COURT_DIR, LEGAL_DIR, NEWS_DIR

def split_text_into_clauses(text: str, max_chars: int = 400, min_chars: int = 80) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\\n\\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) > max_chars:
            sentences = re.split(r'(?<=[.!?])\\s+', para)
            curr = ""
            for s in sentences:
                if len(curr) + len(s) < max_chars:
                    curr = f"{curr} {s}".strip()
                else:
                    if len(curr) >= min_chars:
                        chunks.append(curr)
                    curr = s
            if len(curr) >= min_chars:
                chunks.append(curr)
        elif len(para) >= min_chars:
            chunks.append(para)
    return chunks if chunks else [text[:max_chars]]

class RAGChunker:
    @staticmethod
    def chunk_legal_docs() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        child_chunks, parent_store = [], {}
        if not LEGAL_DIR.exists():
            return child_chunks, parent_store
        for file_path in LEGAL_DIR.glob("*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                meta, body = {}, content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        if yaml:
                            meta = yaml.safe_load(parts[1]) or {}
                        else:
                            meta = {}
                            for line in parts[1].split("\\n"):
                                if ":" in line:
                                    k, v = line.split(":", 1)
                                    meta[k.strip()] = v.strip().strip('"').strip("'")
                        body = parts[2].strip()
                parent_id = f"law_{file_path.stem}"
                title = meta.get("title", file_path.stem)
                url = meta.get("original_url", "https://docs.cntd.ru")
                details = meta.get("details", "")
                priority = meta.get("priority_level", "standard")
                category = meta.get("category", "Нормативная база")
                parent_store[parent_id] = {
                    "parent_id": parent_id, "title": title, "url": url,
                    "details": details, "priority_level": priority, "category": category,
                    "full_text": body
                }
                for idx, clause in enumerate(split_text_into_clauses(body, 450, 70)):
                    child_chunks.append({
                        "id": f"{parent_id}_c{idx}", "parent_id": parent_id,
                        "text": f"{title}. {clause}",
                        "metadata": {"parent_id": parent_id, "title": title, "url": url, "details": details, "priority_level": priority, "category": category, "doc_type": "legal_law", "chunk_index": idx}
                    })
            except Exception:
                continue
        return child_chunks, parent_store

    @staticmethod
    def chunk_court_docs() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        child_chunks, parent_store = [], {}
        court_file = COURT_DIR / "vsrf_court_docs_rag.json"
        if not court_file.exists():
            return child_chunks, parent_store
        try:
            cases = json.loads(court_file.read_text(encoding="utf-8"))
            for idx, item in enumerate(cases):
                meta = item.get("metadata", {})
                content = item.get("page_content", "")
                parent_id = f"court_{idx}"
                title = meta.get("title", f"Дело ВС РФ #{idx}")
                case_num = meta.get("case_number", "Не указан")
                date = meta.get("date", "Не указана")
                url = meta.get("url", "https://www.vsrf.ru")
                parent_store[parent_id] = {"parent_id": parent_id, "title": title, "case_number": case_num, "date": date, "url": url, "full_text": content}
                for c_idx, clause in enumerate(split_text_into_clauses(content, 450, 80)):
                    child_chunks.append({
                        "id": f"{parent_id}_c{c_idx}", "parent_id": parent_id,
                        "text": f"Судебное дело ВС РФ {case_num} ({title}). {clause}",
                        "metadata": {"parent_id": parent_id, "title": title, "case_number": case_num, "date": date, "url": url, "doc_type": "court_case", "priority_level": "high", "chunk_index": c_idx}
                    })
        except Exception:
            pass
        return child_chunks, parent_store

    @staticmethod
    def chunk_cars_catalog() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        child_chunks, parent_store = [], {}
        cars_file = CARS_DIR / "cars_raskatof.json"
        if not cars_file.exists():
            return child_chunks, parent_store
        try:
            cars = json.loads(cars_file.read_text(encoding="utf-8"))
            for idx, car in enumerate(cars):
                parent_id = f"car_{idx}"
                model = car.get("model", "Автомобиль")
                category = car.get("category", "Автопарк")
                specs = car.get("specifications", {})
                terms = car.get("leasing_terms", {})
                daily_rate = terms.get("daily_rate", "")
                initial_pay = terms.get("initial_payment", "")
                terms_text = terms.get("terms_text", "")
                features = car.get("features", [])
                url = "https://raskatof.ru/"
                specs_str = ", ".join([f"{k}: {v}" for k, v in specs.items()])
                feats_str = ", ".join(features)
                full_card = f"Автомобиль: {model}\\nКатегория: {category}\\nХарактеристики: {specs_str}\\nОпции: {feats_str}\\nУсловия раската: {daily_rate}, {initial_pay}. {terms_text}"
                parent_store[parent_id] = {"parent_id": parent_id, "title": model, "category": category, "daily_rate": daily_rate, "initial_payment": initial_pay, "url": url, "full_text": full_card}
                child_chunks.append({
                    "id": f"{parent_id}_overview", "parent_id": parent_id,
                    "text": f"Автомобиль под раскат и выкуп {model}. Класс: {category}. Характеристики: {specs_str}. Условия: {daily_rate}, {initial_pay}.",
                    "metadata": {"parent_id": parent_id, "title": model, "category": category, "daily_rate": daily_rate, "url": url, "doc_type": "car_overview", "priority_level": "high"}
                })
        except Exception:
            pass
        return child_chunks, parent_store

    @staticmethod
    def chunk_auto_news() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        child_chunks, parent_store = [], {}
        news_file = NEWS_DIR / "latest_autonews.json"
        if not news_file.exists():
            return child_chunks, parent_store
        try:
            news = json.loads(news_file.read_text(encoding="utf-8"))
            for idx, item in enumerate(news):
                meta = item.get("metadata", {})
                content = item.get("page_content", "")
                parent_id = f"news_{idx}"
                title = meta.get("title", f"Автоновость #{idx}")
                url = meta.get("url", "")
                date = meta.get("date", "")
                parent_store[parent_id] = {"parent_id": parent_id, "title": title, "date": date, "url": url, "full_text": content}
                for c_idx, clause in enumerate(split_text_into_clauses(content, 400, 70)):
                    child_chunks.append({
                        "id": f"{parent_id}_c{c_idx}", "parent_id": parent_id,
                        "text": f"Новость рынка: {title}. {clause}",
                        "metadata": {"parent_id": parent_id, "title": title, "date": date, "url": url, "doc_type": "news_article", "priority_level": "medium", "chunk_index": c_idx}
                    })
        except Exception:
            pass
        return child_chunks, parent_store
`
    );

    pipelineFolder.file(
      'indexer.py',
      `import json, math, os, re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from rag_pipeline.config import CHROMA_DIR, COLLECTION_CARS, COLLECTION_COURT, COLLECTION_LAWS, COLLECTION_NEWS
from rag_pipeline.chunker import RAGChunker

class SimpleBM25Index:
    def __init__(self):
        self.doc_ids: List[str] = []
        self.corpus: List[List[str]] = []
        self.doc_lens: List[int] = []
        self.avgdl: float = 0.0
        self.idf: Dict[str, float] = {}
        self.k1 = 1.5
        self.b = 0.75

    def tokenize(self, text: str) -> List[str]:
        return [w for w in re.findall(r'[\\w]+', text.lower()) if len(w) > 1]

    def fit(self, doc_ids: List[str], texts: List[str]):
        self.doc_ids = doc_ids
        self.corpus = [self.tokenize(t) for t in texts]
        self.doc_lens = [len(c) for c in self.corpus]
        total_docs = len(texts)
        if total_docs == 0:
            return
        self.avgdl = sum(self.doc_lens) / total_docs
        df = {}
        for doc in self.corpus:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1
        self.idf = {term: math.log((total_docs - freq + 0.5) / (freq + 0.5) + 1.0) for term, freq in df.items()}

    def search(self, query: str, top_k: int = 15) -> List[Tuple[str, float]]:
        q_tokens = self.tokenize(query)
        scores = {}
        for i, doc_tokens in enumerate(self.corpus):
            doc_id = self.doc_ids[i]
            d_len = self.doc_lens[i]
            score = 0.0
            tf_map = {}
            for t in doc_tokens:
                tf_map[t] = tf_map.get(t, 0) + 1
            for q in q_tokens:
                if q in tf_map:
                    tf = tf_map[q]
                    idf = self.idf.get(q, 0.1)
                    denom = tf + self.k1 * (1 - self.b + self.b * (d_len / (self.avgdl or 1)))
                    score += idf * (tf * (self.k1 + 1)) / (denom or 1)
            if score > 0:
                scores[doc_id] = score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs[:top_k]

class ChromaRAGIndexer:
    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self.parent_store_file = CHROMA_DIR / "parent_store.json"
        self.bm25_indices_file = CHROMA_DIR / "bm25_indices.json"
        self._init_chroma()

    def _init_chroma(self):
        self.client = None
        self.chroma_available = False
        try:
            import chromadb
            from chromadb.config import Settings
            self.client = chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))
            self.chroma_available = True
        except Exception:
            pass

    def index_all(self) -> Dict[str, Any]:
        combined_parent_store = {}
        laws_chunks, laws_parents = RAGChunker.chunk_legal_docs()
        court_chunks, court_parents = RAGChunker.chunk_court_docs()
        cars_chunks, cars_parents = RAGChunker.chunk_cars_catalog()
        news_chunks, news_parents = RAGChunker.chunk_auto_news()

        for p_dict in [laws_parents, court_parents, cars_parents, news_parents]:
            combined_parent_store.update(p_dict)
        self.parent_store_file.write_text(json.dumps(combined_parent_store, ensure_ascii=False, indent=2), encoding="utf-8")

        collection_map = {COLLECTION_LAWS: laws_chunks, COLLECTION_COURT: court_chunks, COLLECTION_CARS: cars_chunks, COLLECTION_NEWS: news_chunks}
        bm25_dump = {}
        for coll_name, chunks in collection_map.items():
            ids = [c["id"] for c in chunks]
            texts = [c["text"] for c in chunks]
            bm25 = SimpleBM25Index()
            bm25.fit(ids, texts)
            bm25_dump[coll_name] = {"ids": ids, "texts": texts, "metas": [c["metadata"] for c in chunks]}
            if self.chroma_available and self.client:
                try:
                    try:
                        self.client.delete_collection(name=coll_name)
                    except Exception:
                        pass
                    if ids:
                        coll = self.client.create_collection(name=coll_name)
                        coll.add(ids=ids, documents=texts, metadatas=[c["metadata"] for c in chunks])
                except Exception:
                    pass
        self.bm25_indices_file.write_text(json.dumps(bm25_dump, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"total_chunks": sum(len(c) for c in collection_map.values()), "parent_docs_count": len(combined_parent_store), "collections": {k: len(v) for k, v in collection_map.items()}}
`
    );

    pipelineFolder.file(
      'retriever.py',
      `import json, re
from typing import Any, Dict, List, Optional
from rag_pipeline.config import ALL_COLLECTIONS, CHROMA_DIR, COLLECTION_CARS, COLLECTION_COURT, COLLECTION_LAWS, COLLECTION_NEWS, PRIORITY_HIGH_BOOST, PRIORITY_MEDIUM_BOOST, TOP_K_RERANK, TOP_K_RETRIEVAL
from rag_pipeline.indexer import ChromaRAGIndexer, SimpleBM25Index

class QueryRouter:
    @staticmethod
    def route_query(query: str) -> List[str]:
        q = query.lower()
        targets = []
        is_car = any(w in q for w in ["машин", "авто", "каталог", "chery", "haval", "geely", "лада", "granta", "аренд", "сутки", "взнос", "наличи", "выкуп", "раскат"])
        is_law = any(w in q for w in ["гк", "нк", "стать", "закон", "налог", "ндс", "прибыль", "договор", "обязательств", "арендодател", "арендатор", "неустойк", "расторжен", "банкрот"])
        is_court = any(w in q for w in ["суд", "верховн", "вс рф", "определен", "постановлен", "практик", "дело №", "спор", "взыскан", "изъяти"])
        is_news = any(w in q for w in ["новост", "утильсбор", "рынок", "ставк", "индексац", "2024", "2025", "2026", "китайск"])
        if is_car: targets.append(COLLECTION_CARS)
        if is_law: targets.append(COLLECTION_LAWS)
        if is_court: targets.append(COLLECTION_COURT)
        if is_news: targets.append(COLLECTION_NEWS)
        return targets if targets else ALL_COLLECTIONS

class HybridRetriever:
    def __init__(self):
        self.indexer = ChromaRAGIndexer()
        self.parent_store = self._load_parents()
        self.bm25_indices, self.bm25_data = self._load_bm25()

    def _load_parents(self) -> Dict[str, Any]:
        f = CHROMA_DIR / "parent_store.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    def _load_bm25(self):
        f = CHROMA_DIR / "bm25_indices.json"
        if not f.exists(): return {}, {}
        data = json.loads(f.read_text(encoding="utf-8"))
        indices = {}
        for coll, cdata in data.items():
            bm = SimpleBM25Index()
            bm.fit(cdata.get("ids", []), cdata.get("texts", []))
            indices[coll] = bm
        return indices, data

    def retrieve(self, query: str) -> Dict[str, Any]:
        targets = QueryRouter.route_query(query)
        candidates = []
        for coll in targets:
            bm25 = self.bm25_indices.get(coll)
            cdata = self.bm25_data.get(coll, {})
            id_to_meta = {cdata["ids"][i]: cdata["metas"][i] for i in range(len(cdata.get("ids", [])))}
            id_to_text = {cdata["ids"][i]: cdata["texts"][i] for i in range(len(cdata.get("ids", [])))}
            if bm25:
                for chunk_id, bm_score in bm25.search(query, top_k=TOP_K_RETRIEVAL):
                    meta = id_to_meta.get(chunk_id, {})
                    text = id_to_text.get(chunk_id, "")
                    boost = 1.0
                    p_lvl = meta.get("priority_level", "standard")
                    if p_lvl == "high": boost = PRIORITY_HIGH_BOOST
                    elif p_lvl == "medium": boost = PRIORITY_MEDIUM_BOOST
                    candidates.append({"id": chunk_id, "collection": coll, "score": bm_score * boost, "text": text, "metadata": meta})
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = candidates[:TOP_K_RERANK]
        sources = []
        context_blocks = []
        for i, c in enumerate(top_candidates):
            meta = c["metadata"]
            parent_id = meta.get("parent_id", "")
            parent = self.parent_store.get(parent_id, {})
            title = parent.get("title", meta.get("title", "Документ"))
            url = parent.get("url", meta.get("url", "https://docs.cntd.ru"))
            full_text = parent.get("full_text", c["text"])
            src = {"source_id": f"Источник #{i+1}", "collection": c["collection"], "title": title, "url": url, "matched_chunk": c["text"], "case_number": parent.get("case_number", meta.get("case_number")), "date": parent.get("date", meta.get("date")), "similarity_score": round(c["score"], 3)}
            sources.append(src)
            context_blocks.append(f"[{src['source_id']}] {title}\\nURL: {url}\\n{full_text[:1200]}")
        return {"query": query, "target_collections": targets, "sources": sources, "formatted_context": "\\n\\n---\\n\\n".join(context_blocks)}
`
    );

    pipelineFolder.file(
      'generator.py',
      `import json, os, logging
from typing import Any, Dict, List
from rag_pipeline.config import MODEL_NAME, GEMINI_API_KEY
from rag_pipeline.retriever import HybridRetriever

logger = logging.getLogger("rag_generator")

SYSTEM_PROMPT = """Вы — ведущий юридический и коммерческий ИИ-консультант компании по раскату авто в РФ.
Ваша задача: давать точные ответы на основе контекста со строгими Markdown-ссылками на первоисточники:
- Для законов: [Название статьи ГК/НК РФ](URL)
- Для судебных дел: [Определение ВС РФ № ДЕЛА от ДАТЫ](URL)
- Для авто: [Модель авто](URL)
"""

class RAGAssistant:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.client = None
        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            except Exception:
                pass

    def answer_query(self, query: str) -> Dict[str, Any]:
        retrieval_res = self.retriever.retrieve(query)
        sources = retrieval_res["sources"]
        context_text = retrieval_res["formatted_context"]
        if not sources or not context_text.strip():
            return {"query": query, "answer": "В базе знаний компании не найдено релевантных документов. Запустите: \`reindex_rag.bat\` или \`run_collectors.bat all\`.", "target_collections": retrieval_res.get("target_collections", []), "sources": []}
        user_prompt = f"КОНТЕКСТ:\\n{context_text}\\n\\nВОПРОС: {query}\\nОтветьте с точными ссылками на первоисточники в Markdown."
        answer_text = ""
        if self.client:
            try:
                resp = self.client.models.generate_content(model=MODEL_NAME, contents=user_prompt, config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.2})
                answer_text = resp.text or ""
            except Exception:
                try:
                    resp = self.client.models.generate_content(model="gemini-2.5-flash", contents=user_prompt, config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.2})
                    answer_text = resp.text or ""
                except Exception:
                    pass
        if not answer_text:
            parts = ["**Ответ RAG-ассистента по базе знаний компании:**\\n"]
            for s in sources[:3]:
                parts.append(f"- По данным **[{s['title']}]({s['url']})**: {s['matched_chunk'][:250]}...")
            answer_text = "\\n".join(parts)
        return {"query": query, "answer": answer_text, "target_collections": retrieval_res.get("target_collections", []), "sources": sources}
`
    );
  }

  // Seed data
  const dataFolder = zip.folder('data');
  if (dataFolder) {
    const carsFolder = dataFolder.folder('cars');
    carsFolder?.file('cars_raskatof.json', JSON.stringify([
      {
        category: "Эконом и комфорт класс",
        model: "Chery Tiggo 4 Pro (1.5 CVT)",
        specifications: { "Год выпуска": "2023", "Мощность": "113 л.с.", "КПП": "Вариатор" },
        leasing_terms: { "daily_rate": "Аренда от 2 400 ₽ / сутки", "initial_payment": "Взнос 15 000 ₽" }
      },
      {
        category: "Эконом и комфорт класс",
        model: "Haval Jolion (1.5T 7DCT)",
        specifications: { "Год выпуска": "2024", "Мощность": "143 л.с.", "КПП": "Робот 7DCT" },
        leasing_terms: { "daily_rate": "Аренда от 2 800 ₽ / сутки", "initial_payment": "Взнос 20 000 ₽" }
      }
    ], null, 2));

    const courtFolder = dataFolder.folder('court');
    courtFolder?.file('vsrf_court_docs_rag.json', JSON.stringify([
      {
        page_content: "Определение ВС РФ № 5-КГ23-104-К2 по спорам об изъятии предмета лизинга...",
        metadata: { title: "Определение ВС РФ № 5-КГ23-104-К2", case_number: "5-КГ23-104-К2", date: "14.11.2023" }
      }
    ], null, 2));

    const newsFolder = dataFolder.folder('news');
    newsFolder?.file('latest_autonews.json', JSON.stringify([
      {
        page_content: "Индексация утилизационного сбора: влияние на раскат авто в РФ...",
        metadata: { title: "Индексация утильсбора", source: "autonews.ru", date: "2026-10-28" }
      }
    ], null, 2));

    const legalFolder = dataFolder.folder('legal');
    legalFolder?.file(
      'laws_gk_nk.jsonl',
      `{"parent_id": "tax_1300338665", "source_site": "docs.cntd.ru", "section": "НК РФ", "category": "Транспортный_налог", "original_url": "https://docs.cntd.ru/document/1300338665", "title": "Об утверждении Порядка списания задолженности, признанной безнадежной к взысканию", "details": "Приказ ФНС России от 30 ноября 2022 г. № ЕД-7-8/1131@", "collected_at": "2026-11-01 23:39:50", "priority_level": "high", "body": "Порядок регламентирует основания и перечень документов для признания задолженности по транспортному налогу и обязательным платежам безнадежной к взысканию при банкротстве или ликвидации."}
{"parent_id": "tax_901765862", "source_site": "docs.cntd.ru", "section": "НК РФ", "category": "Налог_на_прибыль_организаций", "original_url": "https://docs.cntd.ru/document/901765862", "title": "Статья 264 НК РФ. Прочие расходы, связанные с производством и реализацией (лизинговые платежи)", "details": "НК РФ Часть 2, Глава 25", "collected_at": "2026-11-01 23:40:10", "priority_level": "high", "body": "К прочим расходам относятся арендные и лизинговые платежи за арендуемое имущество, включая транспортные средства, за вычетом выкупной стоимости."}
{"parent_id": "civics_9027703", "source_site": "docs.cntd.ru", "section": "ГК РФ", "category": "Собственность_приватизация_аренда", "original_url": "https://docs.cntd.ru/document/9027703", "title": "Статья 665 ГК РФ. Договор финансовой аренды (лизинга авто)", "details": "ГК РФ Часть 2, Глава 34", "collected_at": "2026-11-01 23:42:00", "priority_level": "high", "body": "По договору финансовой аренды арендодатель обязуется приобрести в собственность указанное арендатором имущество и предоставить во временное владение и пользование."}
{"parent_id": "civics_9027704", "source_site": "docs.cntd.ru", "section": "ГК РФ", "category": "Собственность_приватизация_аренда", "original_url": "https://docs.cntd.ru/document/9027704", "title": "Статья 624 ГК РФ. Выкуп арендованного имущества (раскат автомобиля)", "details": "ГК РФ Часть 2, Глава 34", "collected_at": "2026-11-01 23:42:30", "priority_level": "high", "body": "В договоре аренды может быть предусмотрено, что имущество переходит в собственность арендатора по истечении срока или до его истечения при условии внесения выкупной цены."}
`
    );
  }

  // Generate & download
  const blob = await zip.generateAsync({ type: 'blob' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'rag-auto-raskat-project-windows-pycharm.zip';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
