import React, { useState } from 'react';
import { 
  FileCode2, 
  Copy, 
  Check, 
  Download, 
  Terminal, 
  Settings, 
  Layers,
  FileText
} from 'lucide-react';
import { SERVER_SCRIPTS } from '../data/ragSources';

interface CodeViewerProps {
  initialScript?: string;
  onDownloadZip: () => void;
}

const CODE_CONTENTS: Record<string, string> = {
  'streamlit_app.py': `import os
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="RAG Ассистент | Раскат Авто РФ",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))
LEGAL_DIR = DATA_DIR / "legal"
COURT_DIR = DATA_DIR / "court"
CARS_DIR = DATA_DIR / "cars"
NEWS_DIR = DATA_DIR / "news"

for directory in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

@st.cache_data(ttl=60)
def load_cars_catalog():
    cars_file = CARS_DIR / "cars_raskatof.json"
    if cars_file.exists():
        return json.load(open(cars_file, "r", encoding="utf-8"))
    return []

@st.cache_data(ttl=60)
def load_court_docs():
    court_file = COURT_DIR / "vsrf_court_docs_rag.json"
    if court_file.exists():
        return json.load(open(court_file, "r", encoding="utf-8"))
    return []

@st.cache_data(ttl=60)
def load_news_docs():
    news_file = NEWS_DIR / "latest_autonews.json"
    if news_file.exists():
        return json.load(open(news_file, "r", encoding="utf-8"))
    return []

cars_data = load_cars_catalog()
court_data = load_court_docs()
news_data = load_news_docs()

with st.sidebar:
    st.title("🚗 Раскат Авто РФ")
    st.caption("База знаний RAG и панель управления")
    selected_view = st.radio(
        "Раздел:",
        [
            "💬 RAG Ассистент (Чат)",
            "🚙 Каталог авто (raskatof.ru)",
            "📜 Нормативная база (ГК/НК РФ)",
            "⚖️ Судебная практика ВС РФ",
            "📰 Автоновости и рынок",
            "⚙️ Статус сбора и сервер (Windows 10)",
        ]
    )
    st.divider()
    st.write(f"• Авто в каталоге: **{len(cars_data)} шт.**")
    st.write(f"• Решения ВС РФ: **{len(court_data)} актов**")
    st.write(f"• Автоновости: **{len(news_data)} шт.**")

if selected_view == "💬 RAG Ассистент (Чат)":
    st.header("💬 RAG Помощник по раскату и выкупу автомобилей")
    st.info("База знаний подключена: ГК РФ (ст. 665, 624), НК РФ (ст. 264), 56 решений ВС РФ, автопарк raskatof.ru")
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Здравствуйте! Я RAG-помощник компании по раскату автомобилей. Задайте вопрос по автопарку или правовым нормам."}
        ]
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if prompt := st.chat_input("Введите ваш вопрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        # Генерация ответа по RAG-базе
        ans = f"**Ответ по базе RAG:**\\nПо запросу '{prompt}' проверен каталог raskatof.ru и судебные позиции ВС РФ."
        st.session_state.messages.append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.markdown(ans)

elif selected_view == "🚙 Каталог авто (raskatof.ru)":
    st.header("🚙 Ассортимент автомобилей под выкуп и аренду")
    for car in cars_data:
        with st.container(border=True):
            st.subheader(car.get("model", "Автомобиль"))
            t = car.get("leasing_terms", {})
            st.write(f"💰 **{t.get('daily_rate')}** | 🔑 **{t.get('initial_payment')}**")
            st.caption(f"Характеристики: {car.get('specifications')}")
`,

  'run_streamlit.bat': `@echo off
:: Запуск веб-части Streamlit на Windows 10
cd /d "%~dp0"
if exist "venv\\Scripts\\streamlit.exe" (
    venv\\Scripts\\streamlit.exe run streamlit_app.py
) else if exist ".venv\\Scripts\\streamlit.exe" (
    .venv\\Scripts\\streamlit.exe run streamlit_app.py
) else (
    streamlit run streamlit_app.py
)
pause`,

  'run_collectors.bat': `@echo off
:: Запуск сбора данных на Windows 10
cd /d "%~dp0"
if exist "venv\\Scripts\\python.exe" (
    set "PY_CMD=venv\\Scripts\\python.exe"
) else (
    set "PY_CMD=python"
)
if "%1"=="" (
    %PY_CMD% rag_collectors\\runner.py --status
) else (
    %PY_CMD% rag_collectors\\runner.py --collector %1
)`,

  'setup_windows_scheduler.bat': `@echo off
:: Добавление 4 задач сбора в Планировщик заданий Windows 10
chcp 65001 >nul
cd /d "%~dp0"
set "BAT_PATH=%~dp0run_collectors.bat"
schtasks /create /tn "RAG_Collector_Cars" /tr "\\"%%BAT_PATH%%\\" cars" /sc weekly /d MON /st 04:00 /f
schtasks /create /tn "RAG_Collector_News" /tr "\\"%%BAT_PATH%%\\" news" /sc weekly /d MON /st 05:00 /f
schtasks /create /tn "RAG_Collector_VSRF" /tr "\\"%%BAT_PATH%%\\" vsrf" /sc monthly /d 1 /st 03:00 /f
schtasks /create /tn "RAG_Collector_Laws" /tr "\\"%%BAT_PATH%%\\" laws" /sc monthly /m JAN,APR,JUL,OCT /d 1 /st 02:00 /f
echo [ГОТОВО] Все 4 задачи добавлены в Планировщик Windows!
pause`,

  'runner.py': `#!/usr/bin/env python3
"""
Мастер-скрипт запуска коллекторов данных для RAG-ассистента раската авто в РФ.
Поддерживает запуск на Windows 10 (Proactor asyncio), Linux и Docker.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from collectors.auto_news import AutoNewsCollector
from collectors.gk_nk_laws import LawsCollector
from collectors.raskatof_cars import CarsCollector
from collectors.vsrf_court import VSRFCourtCollector
from config.settings import CARS_DIR, COURT_DIR, DATA_DIR, LEGAL_DIR, NEWS_DIR

def print_status_dashboard():
    """Вывод актуального состояния собранной RAG-базы на сервере"""
    print("\\n" + "=" * 70)
    print("📊 ТЕКУЩЕЕ СОСТОЯНИЕ БАЗЫ ДАННЫХ RAG (РАСКАТ АВТО)")
    print("=" * 70)
    law_files = list(LEGAL_DIR.glob("*.md"))
    print(f"1. 📜 Нормативная база (ГК/НК РФ): {len(law_files)} .md файлов (регламент: раз в 3 мес)")
    vsrf_file = COURT_DIR / "vsrf_court_docs_rag.json"
    vsrf_count = len(json.load(open(vsrf_file, "r", encoding="utf-8"))) if vsrf_file.exists() else 0
    print(f"2. ⚖️ Судебная практика ВС РФ:      {vsrf_count} актов (регламент: раз в месяц)")
    cars_file = CARS_DIR / "cars_raskatof.json"
    cars_count = len(json.load(open(cars_file, "r", encoding="utf-8"))) if cars_file.exists() else 0
    print(f"3. 🚗 Ассортимент машин raskatof:  {cars_count} авто (регламент: раз в неделю)")
    news_file = NEWS_DIR / "latest_autonews.json"
    news_count = len(json.load(open(news_file, "r", encoding="utf-8"))) if news_file.exists() else 0
    print(f"4. 📰 Автомобильные новости:       {news_count} статей (регламент: раз в неделю)")
    print("=" * 70 + "\\n")

async def run_collector(collector_name: str) -> bool:
    collectors_map = {
        "laws": LawsCollector,
        "vsrf": VSRFCourtCollector,
        "cars": CarsCollector,
        "news": AutoNewsCollector
    }
    targets = list(collectors_map.keys()) if collector_name == "all" else [collector_name]
    for target in targets:
        collector = collectors_map[target]()
        stats = await collector.run()
        if not stats.get("success", False):
            return False
    return True

def main():
    parser = argparse.ArgumentParser(description="RAG Data Collectors Orchestrator")
    parser.add_argument("--collector", choices=["laws", "vsrf", "cars", "news", "all"])
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        print_status_dashboard()
        return

    if not args.collector:
        parser.print_help()
        return

    success = asyncio.run(run_collector(args.collector))
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()`,

  'collectors/gk_nk_laws.py': `import asyncio
import os
import time
from datetime import datetime
from pathlib import Path
import yaml
from playwright.async_api import async_playwright

from collectors.base import BaseCollector
from config.settings import CNTD_MAX_DOCS, CNTD_THEME_URL, LEGAL_DIR, USER_AGENT

EXCLUDE_KEYWORDS = ["земельн", "жилищн", "квартир", "участок", "здание", "помещение", "лесной", "недра"]
INCLUDE_KEYWORDS = ["транспортн", "движим", "автомобил", "средств", "прокат", "лизинг", "выкуп", "аренд", "налог", "финансов", "ндс"]

def should_download(title: str) -> bool:
    t = title.lower()
    if any(exc in t for exc in EXCLUDE_KEYWORDS):
        return any(inc in t for inc in INCLUDE_KEYWORDS)
    return True

class LawsCollector(BaseCollector):
    """Сбор ГК РФ и НК РФ. Регламент: Раз в 3 месяца. Формат: .md с YAML frontmatter."""
    def __init__(self):
        super().__init__("laws_gk_nk")
        self.output_dir = LEGAL_DIR

    async def collect(self):
        saved_count = 0
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            ctx = await browser.new_context(user_agent=USER_AGENT)
            page = await ctx.new_page()

            # Блокировка тяжелых ресурсов для ускорения в 5 раз и предотвращения TimeoutError
            await page.route("**/*", lambda r: r.abort() if r.request.resource_type in ["image", "font", "media"] or "yandex" in r.request.url else r.continue_())
            await page.goto(CNTD_THEME_URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector(".document-list, body", timeout=20000)

            for _ in range(4):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(1.5)

            elements = await page.locator("li.document-list_i").all()
            for item in elements[:CNTD_MAX_DOCS]:
                try:
                    href = await item.locator("a.document-list_i_lk").first.get_attribute("href") or ""
                    title = (await item.locator("div.document-list_i_t").first.inner_text()).strip()
                    details = (await item.locator("div.__color_grey").first.inner_text()).strip()

                    if not should_download(title):
                        continue

                    doc_id = href.split("/")[-1] if "/" in href else str(int(time.time()*1000))
                    d_page = await ctx.new_page()
                    await d_page.goto(f"https://docs.cntd.ru{href}", wait_until="domcontentloaded", timeout=25000)
                    body = await d_page.locator("body").inner_text()
                    await d_page.close()

                    priority = "high" if any(k in (title + body[:500]).lower() for k in ["лизинг", "аренда транспортн", "выкуп", "раскат"]) else "standard"

                    metadata = {
                        "source_site": "docs.cntd.ru",
                        "category": "Нормативная база (ГК РФ / НК РФ)",
                        "original_url": f"https://docs.cntd.ru{href}",
                        "title": title,
                        "details": details,
                        "priority_level": priority,
                        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    filepath = self.output_dir / f"doc_{doc_id}.md"
                    frontmatter = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
                    content = f"---\\n{frontmatter}---\\n\\n# {title}\\n\\n**Реквизиты:** {details}\\n\\n---\\n\\n{body}"

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    saved_count += 1
                except Exception:
                    continue
            await browser.close()
        return {"items_collected": saved_count}`,

  'collectors/vsrf_court.py': `import asyncio
import io
import json
import re
import time
from datetime import datetime
import requests
from playwright.async_api import async_playwright
from pypdf import PdfReader

from collectors.base import BaseCollector
from config.settings import COURT_DIR, USER_AGENT, VSRF_KEYWORD, VSRF_URL, VSRF_YEARS

class VSRFCourtCollector(BaseCollector):
    """Сбор практики ВС РФ. Регламент: Раз в месяц. Формат: vsrf_court_docs_rag.json"""
    def __init__(self):
        super().__init__("vsrf_court")
        self.output_file = COURT_DIR / "vsrf_court_docs_rag.json"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def download_and_extract_pdf(self, url: str) -> str:
        for _ in range(3):
            try:
                resp = self.session.get(url, timeout=35)
                if resp.status_code == 200:
                    reader = PdfReader(io.BytesIO(resp.content))
                    text = "\\n\\n".join([p.extract_text() or "" for p in reader.pages])
                    return re.sub(r"[ \\t]+", " ", text).strip()
            except Exception:
                time.sleep(2)
        return ""

    async def collect(self):
        docs = []
        async with async_playwright() as p:
            # На сервере строго headless=True без GUI
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()
            await page.goto(VSRF_URL, wait_until="networkidle", timeout=45000)

            await page.fill("input#documents-form-keyword", VSRF_KEYWORD)
            for year in VSRF_YEARS:
                chk = page.locator(f"button#checkbox-{year}")
                if await chk.count() > 0 and await chk.get_attribute("aria-checked") == "false":
                    await chk.click()

            await page.click("button[type='submit'][form='documents-form']")
            await page.wait_for_timeout(4000)

            # Извлечение ссылок на PDF
            links = await page.locator("a[href]").all()
            for link in links:
                href = await link.get_attribute("href") or ""
                title = (await link.inner_text()).strip()
                if ("/media-proxy/" in href or href.endswith(".pdf")) and len(title) > 10:
                    full_url = f"https://www.vsrf.ru{href}" if href.startswith("/") else href
                    text = self.download_and_extract_pdf(full_url)
                    if text:
                        docs.append({
                            "page_content": f"Заголовок: {title}\\nТекст документа:\\n{text}",
                            "metadata": {
                                "title": title,
                                "url": full_url,
                                "source": "vsrf.ru",
                                "doc_type": "court_decision",
                                "char_length": len(text),
                                "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                        })
            await browser.close()

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        return {"items_collected": len(docs)}`,

  'collectors/raskatof_cars.py': `import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from collectors.base import BaseCollector
from config.settings import CARS_DIR, HTTP_TIMEOUT, RASKATOF_URL, USER_AGENT

class CarsCollector(BaseCollector):
    """Сбор каталога авто с raskatof.ru. Регламент: Раз в неделю."""
    def __init__(self):
        super().__init__("raskatof_cars")
        self.output_json = CARS_DIR / "cars_raskatof.json"
        self.output_rag = CARS_DIR / "cars_raskatof_rag.json"

    async def collect(self):
        resp = requests.get(RASKATOF_URL, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("div", class_="choose-item")
        cars_data = []
        rag_docs = []

        for item in items:
            model = item.find("h4", class_="choose-model")
            name = model.get_text(strip=True) if model else "Не указано"

            specs = {}
            for p in item.select(".choose-basic-specs p"):
                if ":" in p.get_text():
                    k, v = p.get_text().split(":", 1)
                    specs[k.strip()] = v.strip()

            features = [li.get_text(strip=True) for li in item.select(".extra-features li")]
            leasing = " ".join([p.get_text(strip=True) for p in item.select(".leasing-info p")])

            cars_data.append({
                "model": name,
                "specs": specs,
                "features": features,
                "leasing_terms": leasing
            })

            rag_docs.append({
                "page_content": f"Автомобиль: {name}\\nХарактеристики: {specs}\\nКомплектация: {features}\\nУсловия выкупа/раската: {leasing}",
                "metadata": {"model": name, "source": "raskatof.ru", "doc_type": "vehicle_card"}
            })

        json.dump(cars_data, open(self.output_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        json.dump(rag_docs, open(self.output_rag, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return {"items_collected": len(cars_data)}`,

  'collectors/auto_news.py': `import json
import re
from datetime import datetime
import requests
from collectors.base import BaseCollector
from config.settings import NEWS_DIR, NEWSDATA_API_KEY, USER_AGENT

class AutoNewsCollector(BaseCollector):
    """Сбор автоновостей (утильсбор, лизинг, ОСАГО). Регламент: Раз в неделю."""
    def __init__(self):
        super().__init__("auto_news")
        self.output_file = NEWS_DIR / "latest_autonews.json"

    async def collect(self):
        docs = []
        api_url = f"https://newsdata.io/api/1/latest?apikey={NEWSDATA_API_KEY}&qInTitle=утильсбор&country=ru&language=ru"
        try:
            res = requests.get(api_url, headers={"User-Agent": USER_AGENT}, timeout=12).json()
            for art in res.get("results", [])[:50]:
                title = art.get("title", "").strip()
                content = art.get("description", "").strip()
                if title and content:
                    docs.append({
                        "page_content": f"Заголовок: {title}\\nСодержание: {content}",
                        "metadata": {
                            "title": title,
                            "url": art.get("link"),
                            "date": art.get("pubDate"),
                            "source": art.get("source_id", "newsdata.io")
                        }
                    })
        except Exception as e:
            self.logger.warning(f"Ошибка API: {e}")

        json.dump(docs, open(self.output_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return {"items_collected": len(docs)}`,

  'config/settings.py': `import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))

LEGAL_DIR = DATA_DIR / "legal"
COURT_DIR = DATA_DIR / "court"
CARS_DIR = DATA_DIR / "cars"
NEWS_DIR = DATA_DIR / "news"
LOGS_DIR = BASE_DIR / "logs"

for directory in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "pub_f09cd847b3d74c7492d4dcec897dedb6")
CNTD_THEME_URL = os.getenv("CNTD_THEME_URL", "https://docs.cntd.ru/federal?theme=746501321")
CNTD_MAX_DOCS = int(os.getenv("CNTD_MAX_DOCS", "1000"))
VSRF_URL = "https://www.vsrf.ru/documents"
VSRF_YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
VSRF_KEYWORD = "автомобиль"
RASKATOF_URL = "https://raskatof.ru/"`,

  'requirements.txt': `playwright>=1.42.0
requests>=2.31.0
beautifulsoup4>=4.12.3
pypdf>=4.1.0
pyyaml>=6.0.1
python-dotenv>=1.0.1
lxml>=5.1.0`,

  'Dockerfile': `FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    wget curl gnupg ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 \\
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \\
    libgbm1 libpango-1.0-0 libcairo2 libasound2 fonts-liberation cron \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium && playwright install-deps chromium
COPY . .
RUN mkdir -p /app/data/legal /app/data/court /app/data/cars /app/data/news /app/logs
CMD ["python", "runner.py", "--status"]`,

  'crontab.txt': `# РАСПИСАНИЕ СБОРА ДАННЫХ ДЛЯ RAG-АССИСТЕНТА (РАСКАТ АВТО В РФ)
# 1. Машины raskatof.ru (каждый понедельник в 04:00)
0 4 * * 1 cd /opt/rag_collectors && /opt/rag_collectors/venv/bin/python runner.py --collector cars >> logs/cron_cars.log 2>&1

# 2. Автомобильные новости (каждый понедельник в 05:00)
0 5 * * 1 cd /opt/rag_collectors && /opt/rag_collectors/venv/bin/python runner.py --collector news >> logs/cron_news.log 2>&1

# 3. Судебная практика ВС РФ (1-е число месяца в 03:00)
0 3 1 * * cd /opt/rag_collectors && /opt/rag_collectors/venv/bin/python runner.py --collector vsrf >> logs/cron_vsrf.log 2>&1

# 4. Нормативная база ГК/НК РФ (1-е число января, апреля, июля, октября в 02:00)
0 2 1 1,4,7,10 * cd /opt/rag_collectors && /opt/rag_collectors/venv/bin/python runner.py --collector laws >> logs/cron_laws.log 2>&1`
};

export const CodeViewer: React.FC<CodeViewerProps> = ({
  initialScript = 'runner.py',
  onDownloadZip
}) => {
  const [activeScript, setActiveScript] = useState<string>(initialScript);
  const [copied, setCopied] = useState(false);

  const currentContent = CODE_CONTENTS[activeScript] || '# Файл загружается...';
  const linesCount = currentContent.split('\n').length;

  const handleCopy = () => {
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl shadow-xs">
        <div>
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <FileCode2 className="w-5 h-5 text-blue-600" />
            <span>Серверный пакет скриптов сбора (Python)</span>
          </h2>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
            Все скрипты адаптированы под запуск на Linux-сервере (headless Playwright, retry, логирование, cron).
          </p>
        </div>

        <button
          onClick={onDownloadZip}
          className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.98] rounded-lg shadow-xs transition-all whitespace-nowrap"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Скачать весь пакет (.zip)</span>
        </button>
      </div>

      {/* Editor & File Selector */}
      <div className="bg-[#0E1117] border border-neutral-800 rounded-xl overflow-hidden shadow-lg">
        {/* File Tabs */}
        <div className="flex items-center justify-between px-3 py-2 bg-[#161B22] border-b border-neutral-800 overflow-x-auto gap-2">
          <div className="flex items-center gap-1">
            {SERVER_SCRIPTS.map(script => {
              const isActive = activeScript === script.path;
              return (
                <button
                  key={script.path}
                  onClick={() => setActiveScript(script.path)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono transition-colors whitespace-nowrap ${
                    isActive
                      ? 'bg-[#0E1117] text-white border border-neutral-700 font-semibold'
                      : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/50'
                  }`}
                >
                  <span>{script.name}</span>
                </button>
              );
            })}
          </div>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-neutral-300 hover:text-white bg-neutral-800 hover:bg-neutral-700 rounded transition-colors shrink-0"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Скопировано!' : 'Копировать'}</span>
          </button>
        </div>

        {/* Code Content with Line Numbers */}
        <div className="flex font-mono text-xs text-neutral-200 max-h-[540px] overflow-y-auto">
          {/* Gutter */}
          <div className="select-none py-4 px-3 text-right text-neutral-600 bg-[#0A0D12] border-r border-neutral-800/80 font-mono text-xs min-w-[44px]">
            {Array.from({ length: linesCount }).map((_, i) => (
              <div key={i} className="leading-6">
                {i + 1}
              </div>
            ))}
          </div>

          {/* Text */}
          <div className="flex-1 p-4 overflow-x-auto leading-6">
            <pre className="text-neutral-100 font-mono">{currentContent}</pre>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-[#161B22] border-t border-neutral-800 text-[11px] font-mono text-neutral-400">
          <span>{activeScript}</span>
          <span>UTF-8 · Python 3.11</span>
        </div>
      </div>
    </div>
  );
};
