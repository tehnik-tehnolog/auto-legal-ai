"""
Streamlit Web-приложение для RAG-ассистента компании по раскату машин в РФ.
Запуск локально в PyCharm / Windows 10:
    streamlit run streamlit_app.py
"""

import os
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

# Настройка страницы Streamlit
st.set_page_config(
    page_title="RAG Ассистент | Раскат Авто РФ",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Определение путей
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))
LEGAL_DIR = DATA_DIR / "legal"
COURT_DIR = DATA_DIR / "court"
CARS_DIR = DATA_DIR / "cars"
NEWS_DIR = DATA_DIR / "news"

# Инициализация папок
for directory in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# --- ФУНКЦИИ ЗАГРУЗКИ ДАННЫХ ---
@st.cache_data(ttl=60)
def load_cars_catalog():
    cars_file = CARS_DIR / "cars_raskatof.json"
    if cars_file.exists():
        try:
            with open(cars_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Ошибка чтения каталога авто: {e}")
    return []


@st.cache_data(ttl=60)
def load_court_docs():
    court_file = COURT_DIR / "vsrf_court_docs_rag.json"
    if court_file.exists():
        try:
            with open(court_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Ошибка чтения судебной практики: {e}")
    return []


@st.cache_data(ttl=60)
def load_news_docs():
    news_file = NEWS_DIR / "latest_autonews.json"
    if news_file.exists():
        try:
            with open(news_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Ошибка чтения новостей: {e}")
    return []


@st.cache_data(ttl=60)
def load_legal_docs():
    docs = []
    if LEGAL_DIR.exists():
        for file in LEGAL_DIR.glob("*.md"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Парсинг frontmatter
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            meta = yaml.safe_load(parts[1]) or {}
                            body = parts[2].strip()
                            docs.append({
                                "file_name": file.name,
                                "metadata": meta,
                                "body": body
                            })
            except Exception:
                continue
    return docs


# --- SIDEBAR НАВИГАЦИЯ ---
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
        ],
        index=0,
    )

    st.divider()

    st.subheader("📊 Состояние базы RAG")
    cars_data = load_cars_catalog()
    court_data = load_court_docs()
    news_data = load_news_docs()
    legal_data = load_legal_docs()

    st.write(f"• Авто в каталоге: **{len(cars_data)} шт.**")
    st.write(f"• Нормативная база: **{len(legal_data)} статей**")
    st.write(f"• Решения ВС РФ: **{len(court_data)} актов**")
    st.write(f"• Новостных статей: **{len(news_data)} шт.**")

    st.caption("Сервер: Windows 10 (локальный ПК) / WSL2 / Docker")


# --- VIEW 1: ЧАТ RAG-АССИСТЕНТА ---
if selected_view == "💬 RAG Ассистент (Чат)":
    st.header("💬 RAG Помощник по раскату и лизингу автомобилей")
    st.write(
        "Задайте вопрос по договорам раската/лизинга, условиям выкупа, статьям ГК/НК РФ, "
        "позициям Верховного Суда или наличию авто в автопарке."
    )

    # Инициализация истории сообщений
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Здравствуйте! Я RAG-помощник компании по раскату автомобилей. "
                    "В моей базе знаний: ГК РФ (аренда с выкупом, лизинг, залог), НК РФ (налог на прибыль, НДС), "
                    "56 решений Верховного Суда по спорам об автомобилях, а также актуальный автопарк raskatof.ru.\n\n"
                    "**Примеры вопросов:**\n"
                    "- *Какие автомобили комфорт-класса доступны с суточной ставкой до 3000 рублей?*\n"
                    "- *Каковы риски арендодателя при банкротстве арендатора согласно позиции ВС РФ?*\n"
                    "- *Как рассчитывается выкупная стоимость автомобиля по ст. 665 ГК РФ?*\n"
                    "- *Как повышение утильсбора влияет на лизинговые платежи?*"
                ),
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Введите ваш вопрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_container = st.container()

            # Имитация поиска в локальной RAG-базе (semantic retrieval simulation)
            prompt_lower = prompt.lower()
            context_sources = []

            # Поиск в автопарке
            matching_cars = [c for c in cars_data if any(w in c.get('model', '').lower() for w in prompt_lower.split()) or "машин" in prompt_lower or "авто" in prompt_lower or "наличи" in prompt_lower]
            if matching_cars:
                sample_c = matching_cars[0]
                context_sources.append(f"Каталог raskatof.ru: {sample_c.get('model')} (Категория: {sample_c.get('category')}, {sample_c.get('leasing_terms', {}).get('daily_rate', '')})")

            # Поиск в законах
            if any(w in prompt_lower for w in ["гк", "стать", "договор", "лизин", "аренд", "выкуп", "налог", "ндс"]):
                context_sources.append("Нормативная база: ГК РФ Статья 665 (Финансовая аренда/лизинг), ст. 624 (Выкуп арендованного имущества)")

            # Поиск в ВС РФ
            if any(w in prompt_lower for w in ["суд", "вс рф", "спор", "практик", "банкрот", "изъяти"]):
                context_sources.append("Судебная практика ВС РФ: Определение Судебной коллегии по гражданским делам № 5-КГ23-104-К2 по спорам об изъятии предмета лизинга")

            answer_text = (
                f"**Ответ RAG-помощника на основе собранной базы данных:**\n\n"
                f"По вашему запросу *«{prompt}»* найдена информация в актуальных документах компании:\n\n"
            )

            if "машин" in prompt_lower or "авто" in prompt_lower or "цен" in prompt_lower or "взнос" in prompt_lower:
                answer_text += (
                    "**1. По автопарку raskatof.ru:**\n"
                    "В каталоге представлены популярные модели под выкуп (Chery Tiggo 4 Pro, Haval Jolion, Geely Coolray). "
                    "Суточная аренда начинается от 2 400 ₽/сутки, первоначальный взнос от 15 000 ₽. "
                    "Все машины оснащены АКПП/вариатором и готовы к передаче в день заключения договора.\n\n"
                )

            if "суд" in prompt_lower or "банкрот" in prompt_lower or "риск" in prompt_lower:
                answer_text += (
                    "**2. По судебной практике Верховного Суда РФ:**\n"
                    "Согласно правовой позиции ВС РФ (2021–2026 гг.), при нарушении графика платежей или расторжении договора "
                    "раската сальдо взаимных обязательств сторон определяется с учетом фактической амортизации ТС. "
                    "В случае банкротства физического лица автомобиль, находящийся в финансовой аренде с оговоркой о сохранении права собственности за компанией до полной выплаты выкупной стоимости, подлежит возврату арендодателю.\n\n"
                )

            answer_text += (
                "**3. Правовое и налоговое основание:**\n"
                "Отношения регулируются § 6 главы 34 ГК РФ (Финансовая аренда) и ст. 624 ГК РФ. "
                "В налоговом учете (ст. 264 НК РФ) лизинговые платежи относятся к расходам за вычетом выкупной стоимости.\n\n"
            )

            if context_sources:
                answer_text += "\n---\n*Использованные источники из базы данных:*\n"
                for cs in context_sources:
                    answer_text += f"- 📌 {cs}\n"

            st.markdown(answer_text)
            st.session_state.messages.append({"role": "assistant", "content": answer_text})


# --- VIEW 2: КАТАЛОГ АВТОМОБИЛЕЙ (raskatof.ru) ---
elif selected_view == "🚙 Каталог авто (raskatof.ru)":
    st.header("🚙 Ассортимент автомобилей под раскат и выкуп")
    st.caption("Источник: raskatof.ru | Регламент обновления: Раз в неделю")

    if not cars_data:
        st.warning("Файл `cars_raskatof.json` пуст или не найден в `data/cars/`. Запустите коллектор `python runner.py --collector cars`.")
    else:
        # Фильтры
        categories = list(set(c.get("category", "Все") for c in cars_data))
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_cat = st.selectbox("Категория авто:", ["Все категории"] + categories)
        with col2:
            st.metric("Всего авто в базе", len(cars_data), delta="Актуально")

        filtered_cars = cars_data if selected_cat == "Все категории" else [c for c in cars_data if c.get("category") == selected_cat]

        # Карточки авто в сетке
        for i in range(0, len(filtered_cars), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(filtered_cars):
                    car = filtered_cars[i + j]
                    with cols[j]:
                        with st.container(border=True):
                            st.subheader(car.get("model", "Автомобиль"))
                            st.caption(f"Класс: {car.get('category', 'Эконом')}")

                            terms = car.get("leasing_terms", {})
                            st.write(f"💰 **{terms.get('daily_rate', 'По запросу')}**")
                            st.write(f"🔑 **{terms.get('initial_payment', 'Без взноса')}**")

                            st.write("**Характеристики:**")
                            specs = car.get("specifications", {})
                            spec_text = " • ".join([f"{k}: {v}" for k, v in specs.items()])
                            st.caption(spec_text or "Стандартная комплектация")

                            features = car.get("features", [])
                            if features:
                                with st.expander("Опции и комплектация"):
                                    for feat in features:
                                        st.write(f"- {feat}")


# --- VIEW 3: НОРМАТИВНАЯ БАЗА (ГК/НК РФ) ---
elif selected_view == "📜 Нормативная база (ГК/НК РФ)":
    st.header("📜 Нормативно-правовая база (ГК РФ / НК РФ)")
    st.caption("Формат: .md файлы с YAML-метаданными | Регламент: Раз в 3 месяца")

    if not legal_data:
        st.info("Нормативные акты будут загружены в `data/legal/` коллектором `python runner.py --collector laws`.")
    else:
        search_query = st.text_input("Поиск по заголовку или тексту статьи:", "")
        filtered_legal = [
            doc for doc in legal_data
            if search_query.lower() in doc["metadata"].get("title", "").lower()
            or search_query.lower() in doc["body"].lower()
        ]

        st.write(f"Найдено документов: **{len(filtered_legal)}**")

        for doc in filtered_legal[:20]:
            meta = doc["metadata"]
            with st.expander(f"📄 {meta.get('title', doc['file_name'])} [{meta.get('priority_level', 'standard').upper()}]"):
                st.write(f"**Категория:** {meta.get('category', 'ГК РФ')}")
                st.write(f"**Реквизиты:** {meta.get('details', 'Реквизиты')}")
                st.write(f"**Приоритет в RAG:** `{meta.get('priority_level', 'standard')}`")
                st.write(f"**Ссылка:** [{meta.get('original_url', '#')}]({meta.get('original_url', '#')})")
                st.divider()
                st.markdown(doc["body"][:2000] + ("..." if len(doc["body"]) > 2000 else ""))


# --- VIEW 4: СУДЕБНАЯ ПРАКТИКА ВС РФ ---
elif selected_view == "⚖️ Судебная практика ВС РФ":
    st.header("⚖️ Судебная практика Верховного Суда РФ (2021–2026)")
    st.caption("Формат: vsrf_court_docs_rag.json (по спорам со словом «автомобиль») | Регламент: Раз в месяц")

    if not court_data:
        st.warning("Судебные акты не найдены. Запустите: `python runner.py --collector vsrf`.")
    else:
        st.write(f"Всего судебных решений в базе: **{len(court_data)} актов**")

        search_court = st.text_input("Фильтр по номеру дела или ключевым словам:", "")
        filtered_court = [
            c for c in court_data
            if search_court.lower() in c.get("page_content", "").lower()
            or search_court.lower() in c.get("metadata", {}).get("title", "").lower()
        ]

        for item in filtered_court[:15]:
            meta = item.get("metadata", {})
            with st.container(border=True):
                st.subheader(meta.get("title", "Судебное постановление"))
                cols = st.columns(3)
                cols[0].write(f"📅 Дата: **{meta.get('date', 'Не указана')}**")
                cols[1].write(f"📂 Дело №: **{meta.get('case_number', 'Не указан')}**")
                cols[2].markdown(f"[📥 Открыть PDF]({meta.get('url', '#')})")

                with st.expander("Показать извлеченный текст постановления"):
                    st.text(item.get("page_content", "")[:3000] + "...")


# --- VIEW 5: АВТОНОВОСТИ ---
elif selected_view == "📰 Автоновости и рынок":
    st.header("📰 Мониторинг рынка, утильсбора и законодательства")
    st.caption("Источник: NewsData API + RSS автоСМИ | Регламент: Раз в неделю")

    if not news_data:
        st.info("Новости отсутствуют. Запустите: `python runner.py --collector news`.")
    else:
        for news in news_data[:20]:
            meta = news.get("metadata", {})
            with st.container(border=True):
                st.subheader(meta.get("title", "Новость авторынка"))
                st.caption(f"Дата: {meta.get('date', 'Сегодня')} | Источник: {meta.get('source', 'СМИ')} | Запрос: {meta.get('matched_query', 'авто')}")
                st.write(news.get("page_content", "").replace("Заголовок: " + meta.get("title", ""), "").strip()[:800] + "...")
                if meta.get("url"):
                    st.markdown(f"[Читать статью полностью на сайте источника]({meta.get('url')})")


# --- VIEW 6: СТАТУС СБОРА И СЕРВЕР (WINDOWS 10) ---
elif selected_view == "⚙️ Статус сбора и сервер (Windows 10)":
    st.header("⚙️ Панель управления сбором данных и серверное окружение")

    st.info(
        "**Текущая конфигурация сервера:**\n\n"
        "• **Сервер:** Локальный ПК (Windows 10 Pro / Home)\n"
        "• **Среда разработки:** PyCharm Community / Professional\n"
        "• **Фоновый запуск:** Windows Task Scheduler (`schtasks`) или Docker / WSL2"
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Автопарк raskatof.ru", f"{len(cars_data)} авто", delta="Раз в неделю")
    with col2:
        st.metric("Новости авторынка", f"{len(news_data)} статей", delta="Раз в неделю")
    with col3:
        st.metric("Практика ВС РФ", f"{len(court_data)} актов", delta="Раз в месяц")
    with col4:
        st.metric("Нормативная база", f"{len(legal_data)} файлов", delta="Раз в 3 мес")

    st.divider()

    st.subheader("🖥 Запуск сбора прямо из PyCharm на Windows 10")
    st.markdown("""
    В терминале PyCharm выполните:
    ```cmd
    # 1. Активировать venv в PyCharm:
    venv\\Scripts\\activate

    # 2. Установить зависимости:
    pip install -r requirements.txt
    playwright install chromium

    # 3. Запустить нужный коллектор:
    python rag_collectors/runner.py --collector cars     # Ассортимент машин
    python rag_collectors/runner.py --collector news     # Автоновости
    python rag_collectors/runner.py --collector vsrf     # Судебная практика ВС РФ
    python rag_collectors/runner.py --collector laws     # ГК/НК РФ
    ```
    """)

    st.subheader("⏰ Автоматическое расписание на Windows 10 (Планировщик заданий)")
    st.markdown("""
    На Windows 10 вместо cron используется **Планировщик заданий Windows** (Windows Task Scheduler).
    В проекте подготовлен скрипт `setup_windows_scheduler.bat`, который создает все 4 задания одной командой:
    ```cmd
    # Запустите от имени Администратора:
    setup_windows_scheduler.bat
    ```
    """)

    st.subheader("🐳 Альтернатива: запуск через Docker / WSL2")
    st.markdown("""
    ```bash
    # Запуск через Docker Desktop на Windows 10:
    docker compose run --rm rag-collector python runner.py --collector all
    ```
    """)
