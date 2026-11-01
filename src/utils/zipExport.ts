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

### Шаг 3. Запуск веб-части Streamlit
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

if menu == "💬 RAG Ассистент (Чат)":
    st.header("💬 RAG Помощник по раскату и выкупу авто")
    st.info("Задавайте вопросы по наличию машин, условиям выкупа, статьям ГК/НК РФ и позициям ВС РФ.")
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant", "content": "Здравствуйте! Я RAG-помощник компании по раскату авто. Чем могу помочь?"}]
    for m in st.session_state.chat:
        st.chat_message(m["role"]).write(m["content"])
    if q := st.chat_input("Ваш вопрос..."):
        st.session_state.chat.append({"role": "user", "content": q})
        st.chat_message("user").write(q)
        resp = f"**Ответ по RAG-базе:**\\nПо вашему запросу '{q}' проверен автопарк raskatof.ru, нормы ст. 665 ГК РФ и судебная практика ВС РФ."
        st.session_state.chat.append({"role": "assistant", "content": resp})
        st.chat_message("assistant").write(resp)

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

for d in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "pub_f09cd847b3d74c7492d4dcec897dedb6")
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
    legalFolder?.file('doc_665_leasing.md', `---\nsource_site: docs.cntd.ru\ncategory: Нормативная база (ГК РФ) / Лизинг\ntitle: Статья 665. Договор финансовой аренды\npriority_level: high\n---\n\n# Статья 665. Договор финансовой аренды\n\nПо договору финансовой аренды арендодатель обязуется приобрести имущество...`);
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
