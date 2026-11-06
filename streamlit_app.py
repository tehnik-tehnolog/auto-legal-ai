"""
Streamlit Web-приложение для RAG-ассистента компании по раскату машин в РФ.
Запуск локально в PyCharm / Windows 10:
    streamlit run streamlit_app.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
import yaml

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
PDD_DIR = DATA_DIR / "pdd"
LOGS_DIR = BASE_DIR / "logs"

# Путь к единому файлу нормативной базы и ПДД
LEGAL_JSONL_FILE = LEGAL_DIR / "laws_gk_nk.jsonl"
PDD_RULES_FILE = PDD_DIR / "pdd_rules_rag.json"

# Инициализация папок
for directory in [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, PDD_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# --- ФУНКЦИИ ЗАГРУЗКИ ДАННЫХ ---
@st.cache_data(ttl=60)
def load_pdd_rules():
    if PDD_RULES_FILE.exists():
        try:
            with open(PDD_RULES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Ошибка чтения базы ПДД: {e}")
    return []


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
    """
    Загрузка нормативных актов (ГК РФ / НК РФ).
    Приоритетно читает из единого файла JSONL (laws_gk_nk.jsonl).
    При его отсутствии обращается к .md файлам.
    """
    docs = []
    # 1. Чтение из единого JSONL файла
    if LEGAL_JSONL_FILE.exists():
        try:
            with open(LEGAL_JSONL_FILE, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if line:
                        try:
                            doc = json.loads(line)
                            docs.append({
                                "parent_id": doc.get("parent_id", f"doc_{idx}"),
                                "source_site": doc.get("source_site", "docs.cntd.ru"),
                                "section": doc.get("section", "НК РФ" if doc.get("parent_id", "").startswith("tax_") else "ГК РФ"),
                                "category": doc.get("category", "Нормативная база"),
                                "original_url": doc.get("original_url", doc.get("url", "https://docs.cntd.ru")),
                                "title": doc.get("title", f"Документ #{idx}"),
                                "details": doc.get("details", ""),
                                "collected_at": doc.get("collected_at", ""),
                                "priority_level": doc.get("priority_level", "standard"),
                                "body": doc.get("body", doc.get("full_text", ""))
                            })
                        except Exception:
                            continue
        except Exception as e:
            st.error(f"Ошибка чтения JSONL базы законов: {e}")

    # 2. Фоллбэк на .md файлы, если JSONL пока пуст
    if not docs and LEGAL_DIR.exists():
        for file in LEGAL_DIR.glob("*.md"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            meta = yaml.safe_load(parts[1]) or {}
                            body = parts[2].strip()
                            pid = f"civics_{file.stem}" if "665" in file.stem else f"tax_{file.stem}"
                            cat = meta.get("category", "Нормативная база")
                            sec = "НК РФ" if "нк" in cat.lower() or "налог" in cat.lower() else "ГК РФ"
                            docs.append({
                                "parent_id": pid,
                                "source_site": meta.get("source_site", "docs.cntd.ru"),
                                "section": sec,
                                "category": cat,
                                "original_url": meta.get("original_url", "#"),
                                "title": meta.get("title", file.name),
                                "details": meta.get("details", ""),
                                "collected_at": meta.get("collected_at", ""),
                                "priority_level": meta.get("priority_level", "standard"),
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
            "🚦 Правила дорожного движения (ПДД РФ)",
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
    pdd_data = load_pdd_rules()

    tax_docs_count = sum(1 for d in legal_data if d.get("section") == "НК РФ" or d.get("parent_id", "").startswith("tax_"))
    civics_docs_count = sum(1 for d in legal_data if d.get("section") == "ГК РФ" or d.get("parent_id", "").startswith("civics_"))

    st.write(f"• Авто в каталоге: **{len(cars_data)} шт.**")
    st.write(f"• Законы (JSONL): **{len(legal_data)}** (НК: {tax_docs_count}, ГК: {civics_docs_count})")
    st.write(f"• ПДД РФ (абзацы): **{len(pdd_data)} пунктов**")
    st.write(f"• Решения ВС РФ: **{len(court_data)} актов**")
    st.write(f"• Новостных статей: **{len(news_data)} шт.**")

    # Кнопка быстрой выборочной переиндексации (Машины + Новости)
    if st.button("🔄 Переиндексировать только (Машины + Новости)", use_container_width=True, type="primary"):
        with st.spinner("Быстрая переиндексация каталога авто и новостей..."):
            try:
                from rag_pipeline.indexer import ChromaRAGIndexer
                indexer = ChromaRAGIndexer()
                res = indexer.index_partial(["car_catalog", "auto_news"], verbose=False)
                st.success(f"⚡ Быстро обновлено {res['total_chunks']} чанков за {res['duration_sec']} с!")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка частичной индексации: {e}")

    # Кнопка полной переиндексации
    if st.button("⚡ Полная переиндексация (Все 5 коллекций)", use_container_width=True):
        with st.spinner("Полная переиндексация 5 коллекций..."):
            try:
                from rag_pipeline.indexer import ChromaRAGIndexer
                indexer = ChromaRAGIndexer()
                res = indexer.index_all(verbose=False)
                st.success(f"Индексация завершена! Чанков: {res['total_chunks']}, Документов: {res['parent_docs_count']}")
                st.rerun()
            except Exception as e:
                st.error(f"Ошибка индексации: {e}")

    st.caption("Сервер: Windows 10 (локальный ПК) / WSL2 / Docker")


# --- VIEW 1: ЧАТ RAG-АССИСТЕНТА ---
if selected_view == "💬 RAG Ассистент (Чат)":
    st.header("💬 RAG Помощник по раскату и лизингу автомобилей")
    st.caption("Пайплайн: Query Router ➔ BM25 + Dense ➔ Metadata Boost ➔ Reranker ➔ Gemini 3.1 Flash Lite")

    # Инициализация истории сообщений
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Здравствуйте! Я RAG-помощник компании по раскату автомобилей в РФ.\n\n"
                    "В моей базе знаний:\n"
                    "- **НК РФ** (транспортный налог, списание безнадежной задолженности, налог на прибыль по ст. 264, НДС)\n"
                    "- **ГК РФ** (лизинг по ст. 665, аренда с выкупом по ст. 624, аренда ТС без экипажа по ст. 642, банкротство)\n"
                    "- **Практика ВС РФ** (56 определений по спорам о защите прав потребителей и изъятии авто)\n"
                    "- **Автопарк raskatof.ru** (комплектации, суточные ставки, выкупные условия)\n\n"
                    "**Примеры вопросов:**\n"
                    "- *Как рассчитывается списание задолженности по транспортному налогу?*\n"
                    "- *Какие автомобили комфорт-класса доступны с суточной ставкой до 3000 рублей?*\n"
                    "- *Каковы риски арендодателя при банкротстве арендатора согласно позиции ВС РФ?*\n"
                    "- *Как выкупная стоимость автомобиля учитывается в составе расходов по налогу на прибыль?*"
                ),
                "sources": []
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("targets"):
                target_labels = {
                    "car_catalog": "🚗 Автопарк raskatof.ru",
                    "legal_laws": "📜 Законы (ГК/НК РФ)",
                    "court_cases": "⚖️ ВС РФ (Судебная практика)",
                    "auto_news": "📰 Автоновости и рынок",
                    "traffic_rules": "🚦 ПДД РФ"
                }
                badges = [target_labels.get(t, t) for t in msg["targets"]]
                st.caption(f"🎯 **Коллекции поиска (Query Router):** {' • '.join(badges)}")

            if msg.get("fallback_used"):
                with st.expander("ℹ️ Статус подключения Gemini (загружен локальный генератор)"):
                    st.warning(f"Причина вызова локального синтеза: **{msg.get('fallback_reason')}**")
                    st.caption("Подробный лог сохранен в: `logs/gemini_connection.log`")

            st.markdown(msg["content"])

            if msg.get("sources"):
                with st.expander(f"📚 Использованные первоисточники ({len(msg['sources'])} документов)"):
                    st.caption("ℹ️ *RRF Score в диапазоне 0.030–0.055 отражает топ-ранг одновременно в семантическом (Dense) и лексическом (BM25) поиске.*")
                    for s in msg["sources"]:
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.markdown(f"**[{s['title']}]({s['url']})**")
                            if s.get("case_number"):
                                st.caption(f"Дело №: {s['case_number']} | Дата: {s.get('date', 'Не указана')}")
                            st.text(f"Фрагмент: {s['matched_chunk'][:240]}...")
                        with col_b:
                            st.metric("Rerank Score", f"{s.get('similarity_score', 0.0):.3f}", help="RRF Score (Reciprocal Rank Fusion). 0.030–0.055 — высший показатель совпадения в Dense + BM25.")
                        st.divider()

    if prompt := st.chat_input("Введите ваш вопрос..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Поиск по разделенным коллекциям (Router + BM25 + Dense + Stratified Reranker)..."):
                try:
                    from rag_pipeline.generator import RAGAssistant
                    assistant = RAGAssistant()
                    rag_result = assistant.answer_query(prompt)
                    answer_text = rag_result["answer"]
                    targets = rag_result.get("target_collections", [])
                    sources = rag_result.get("sources", [])
                    fallback_used = rag_result.get("fallback_used", False)
                    fallback_reason = rag_result.get("fallback_reason")
                except Exception as rag_err:
                    answer_text = f"Ошибка RAG пайплайна: {rag_err}"
                    targets = []
                    sources = []
                    fallback_used = False
                    fallback_reason = None

            # Отображаем плашку роутера
            if targets:
                target_labels = {
                    "car_catalog": "🚗 Автопарк raskatof.ru",
                    "legal_laws": "📜 Законы (ГК/НК РФ)",
                    "court_cases": "⚖️ ВС РФ (Судебная практика)",
                    "auto_news": "📰 Автоновости и рынок",
                    "traffic_rules": "🚦 ПДД РФ"
                }
                badges = [target_labels.get(t, t) for t in targets]
                st.caption(f"🎯 **Коллекции поиска (Query Router):** {' • '.join(badges)}")

            if fallback_used:
                with st.expander("ℹ️ Статус подключения Gemini (загружен локальный генератор)"):
                    st.warning(f"Причина: **{fallback_reason}**")
                    st.caption("Подробный лог сохранен в: `logs/gemini_connection.log`")

            st.markdown(answer_text)

            if sources:
                with st.expander(f"📚 Использованные первоисточники ({len(sources)} документов)"):
                    st.caption("ℹ️ *RRF Score в диапазоне 0.030–0.055 отражает топ-ранг одновременно в семантическом (Dense) и лексическом (BM25) поиске.*")
                    for s in sources:
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.markdown(f"**[{s['title']}]({s['url']})**")
                            if s.get("case_number"):
                                st.caption(f"Дело №: {s['case_number']} | Дата: {s.get('date', 'Не указана')}")
                            st.text(f"Фрагмент: {s['matched_chunk'][:240]}...")
                        with col_b:
                            st.metric("Rerank Score", f"{s.get('similarity_score', 0.0):.3f}", help="RRF Score (Reciprocal Rank Fusion). 0.030–0.055 — высший показатель совпадения в Dense + BM25.")
                        st.divider()

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer_text,
                "targets": targets,
                "sources": sources,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason
            })


# --- VIEW 2: КАТАЛОГ АВТОМОБИЛЕЙ (raskatof.ru) ---
elif selected_view == "🚙 Каталог авто (raskatof.ru)":
    st.header("🚙 Ассортимент автомобилей под раскат и выкуп")
    st.caption("Источник: raskatof.ru | Регламент обновления: Раз в неделю")

    if not cars_data:
        st.warning("Файл `cars_raskatof.json` пуст или не найден в `data/cars/`. Запустите коллектор `python runner.py --collector cars`.")
    else:
        categories = list(set(c.get("category", "Все") for c in cars_data))
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_cat = st.selectbox("Категория авто:", ["Все категории"] + categories)
        with col2:
            st.metric("Всего авто в базе", len(cars_data), delta="Актуально")

        filtered_cars = cars_data if selected_cat == "Все категории" else [c for c in cars_data if c.get("category") == selected_cat]

        for i in range(0, len(filtered_cars), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(filtered_cars):
                    car = filtered_cars[i + j]
                    with cols[j]:
                        with st.container(border=True):
                            model_display = car.get("model") or car.get("title") or car.get("name") or "Автомобиль"
                            st.subheader(model_display)
                            st.caption(f"Класс: {car.get('category', 'Эконом и комфорт класс')}")

                            terms = car.get("leasing_terms") or car.get("leasing_info") or {}
                            if isinstance(terms, dict):
                                daily = terms.get("daily_rate") or terms.get("daily") or "По запросу"
                                initial = terms.get("initial_payment") or terms.get("initial") or "Без первого взноса"
                            else:
                                daily = str(terms)
                                initial = "По запросу"

                            st.write(f"💰 **{daily}**")
                            st.write(f"🔑 **{initial}**")

                            st.write("**Характеристики:**")
                            specs = car.get("specifications") or car.get("specs") or {}
                            if isinstance(specs, dict):
                                spec_text = " • ".join([f"{k}: {v}" for k, v in specs.items()])
                            elif isinstance(specs, list):
                                spec_text = " • ".join(str(s) for s in specs)
                            else:
                                spec_text = str(specs)
                            st.caption(spec_text or "Стандартная комплектация")

                            features = car.get("features") or car.get("options") or []
                            if features:
                                with st.expander("Опции и комплектация"):
                                    for feat in features:
                                        st.write(f"- {feat}")


# --- VIEW 3: НОРМАТИВНАЯ БАЗА (ГК/НК РФ) ---
elif selected_view == "📜 Нормативная база (ГК/НК РФ)":
    st.header("📜 Нормативно-правовая база (ГК РФ / НК РФ / КоАП РФ / Лизинг)")
    st.caption("Формат: Единый файл `data/legal/laws_gk_nk.jsonl` | Шаблон ID: `{prefix}_{хэш title}_{хэш details}`")

    if not legal_data:
        st.info("Нормативные акты будут загружены в `data/legal/laws_gk_nk.jsonl` коллектором `python runner.py --collector laws`.")
    else:
        # Фильтры по разделу и категории
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        all_secs = sorted(list(set(d.get("section", "Общее") for d in legal_data if d.get("section"))))
        with col_f1:
            selected_section = st.selectbox("Раздел законодательства:", ["Все разделы"] + all_secs)
        with col_f2:
            all_cats = sorted(list(set(d.get("category", "") for d in legal_data if d.get("category"))))
            selected_category = st.selectbox("Категория (тема):", ["Все категории"] + all_cats)
        with col_f3:
            search_query = st.text_input("Поиск по заголовку, номеру или тексту статьи:", "")

        filtered_legal = legal_data

        if selected_section != "Все разделы":
            filtered_legal = [d for d in filtered_legal if d.get("section") == selected_section]

        if selected_category != "Все категории":
            filtered_legal = [d for d in filtered_legal if d.get("category") == selected_category]

        if search_query.strip():
            sq = search_query.lower()
            filtered_legal = [
                d for d in filtered_legal
                if sq in d.get("title", "").lower()
                or sq in d.get("parent_id", "").lower()
                or sq in d.get("details", "").lower()
                or sq in d.get("body", "").lower()
            ]

        st.write(f"Найдено документов: **{len(filtered_legal)}** из {len(legal_data)}")

        for doc in filtered_legal[:30]:
            pid = doc.get("parent_id", "doc")
            sec = doc.get("section", "Закон")
            cat = doc.get("category", "Общее")
            title = doc.get("title", "Нормативный акт")
            p_lvl = doc.get("priority_level", "standard").upper()

            with st.expander(f"📄 [{pid}] {title} ({sec} / {cat})"):
                c1, c2, c3 = st.columns([1, 1, 1])
                c1.write(f"**Раздел:** `{sec}`")
                c1.write(f"**Parent ID:** `{pid}`")
                c2.write(f"**Категория:** `{cat}`")
                c2.write(f"**Приоритет в RAG:** `{p_lvl}`")
                c3.write(f"**Сбор:** `{doc.get('collected_at', 'Не указано')}`")
                c3.markdown(f"**Первоисточник:** [{doc.get('original_url', '#')}]({doc.get('original_url', '#')})")

                st.write(f"**Реквизиты:** {doc.get('details', 'Реквизиты отсутствуют')}")
                st.divider()
                st.markdown(doc.get("body", "")[:2500] + ("..." if len(doc.get("body", "")) > 2500 else ""))


# --- VIEW 3.5: ПРАВИЛА ДОРОЖНОГО ДВИЖЕНИЯ (ПДД РФ) ---
elif selected_view == "🚦 Правила дорожного движения (ПДД РФ)":
    st.header("🚦 Правила дорожного движения РФ (ПДД РФ)")
    st.caption("Источник: ГИБДД РФ PDF (`Pravila_dorozhnogo_dvizheniya.pdf`) | Чанкинг: По абзацам / пунктам")

    if not pdd_data:
        st.warning("Файл ПДД не найден в `data/pdd/pdd_rules_rag.json`. Запустите коллектор `python runner.py --collector pdd`.")
    else:
        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            sections_list = ["Все разделы"] + sorted(list(set(p.get("section_title", "ПДД") for p in pdd_data)))
            selected_pdd_sec = st.selectbox("Раздел ПДД:", sections_list)
        with col_p2:
            st.metric("Всего пунктов в базе", len(pdd_data), delta="Абзацный чанкинг")

        pdd_filter = pdd_data if selected_pdd_sec == "Все разделы" else [p for p in pdd_data if p.get("section_title") == selected_pdd_sec]

        search_pdd = st.text_input("Поиск по пункту ПДД или теме (скорость, обгон, ДТП, штрафы):", "")
        if search_pdd.strip():
            sq = search_pdd.lower()
            pdd_filter = [
                p for p in pdd_filter
                if sq in p.get("paragraph_text", "").lower()
                or sq in p.get("clause_number", "").lower()
                or sq in p.get("topic", "").lower()
            ]

        st.write(f"Найдено пунктов: **{len(pdd_filter)}**")

        for item in pdd_filter[:25]:
            sec_name = item.get("section_title", "ПДД РФ")
            clause_no = item.get("clause_number", "")
            topic = item.get("topic", sec_name)
            text = item.get("paragraph_text", "")

            with st.container(border=True):
                st.markdown(f"**🚦 {sec_name} | Пункт {clause_no}** — *{topic}*")
                st.write(text)



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
        "• **Фоновый запуск:** Windows Task Scheduler (`schtasks`) или Docker / WSL2\n"
        "• **Хранилище законов:** Единый файл `data/legal/laws_gk_nk.jsonl` (14 целевых актов)\n"
        "• **Правила дорожного движения:** Абзацный чанкинг `data/pdd/pdd_rules_rag.json`"
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Автопарк raskatof", f"{len(cars_data)} авто", delta="Раз в неделю")
    with col2:
        st.metric("Новости авторынка", f"{len(news_data)} статей", delta="Раз в неделю")
    with col3:
        st.metric("ПДД РФ (абзацы)", f"{len(pdd_data)} пунктов", delta="По абзацам")
    with col4:
        st.metric("Практика ВС РФ", f"{len(court_data)} актов", delta="Раз в месяц")
    with col5:
        st.metric("Законы (ГК/НК/КоАП)", f"{len(legal_data)} актов", delta="JSONL")

    st.subheader("⚡ Управление индексами ChromaDB")
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("🔄 Переиндексировать только (Машины + Новости)", use_container_width=True, type="primary", key="btn_partial_reindex"):
            with st.spinner("Быстрая переиндексация автопарка и новостей..."):
                from rag_pipeline.indexer import ChromaRAGIndexer
                res = ChromaRAGIndexer().index_partial(["car_catalog", "auto_news"], verbose=False)
                st.success(f"Быстро обновлено {res['total_chunks']} чанков за {res['duration_sec']} с!")
                st.rerun()
    with col_act2:
        if st.button("⚡ Полная переиндексация всех 5 коллекций", use_container_width=True, key="btn_full_reindex"):
            with st.spinner("Индексация законов, решений ВС, каталога, новостей и ПДД..."):
                from rag_pipeline.indexer import ChromaRAGIndexer
                res = ChromaRAGIndexer().index_all(verbose=False)
                st.success(f"Полная база переиндексирована: {res['total_chunks']} чанков, {res['parent_docs_count']} документов!")
                st.rerun()

    st.divider()

    # Секция подробного просмотра логов
    st.subheader("📋 Системные логи и диагностика")
    st.caption("Подробный аудит подключений к Gemini, переиндексации ChromaDB и работы коллекторов.")

    log_files_map = {
        "Gemini Connection & Fallbacks (gemini_connection.log)": LOGS_DIR / "gemini_connection.log",
        "RAG ChromaDB Indexer (rag_indexer.log)": LOGS_DIR / "rag_indexer.log",
        "Laws Collector Detailed (laws_collector_detailed.log)": LOGS_DIR / "laws_collector_detailed.log",
        "Cars raskatof.ru Collector (raskatof_cars.log)": LOGS_DIR / "raskatof_cars.log",
        "PDD Rules Collector (pdd_rules.log)": LOGS_DIR / "pdd_rules.log",
        "Supreme Court Collector (vsrf_court.log)": LOGS_DIR / "vsrf_court.log",
        "News Collector (auto_news.log)": LOGS_DIR / "auto_news.log"
    }

    selected_log_name = st.selectbox("Выберите файл логов для просмотра:", list(log_files_map.keys()))
    selected_log_path = log_files_map[selected_log_name]

    if st.button("🔄 Обновить лог", use_container_width=False):
        st.rerun()

    if selected_log_path.exists():
        try:
            with open(selected_log_path, "r", encoding="utf-8") as lf:
                log_content = lf.read()
                if log_content.strip():
                    st.code(log_content[-5000:], language="log")
                else:
                    st.info(f"Файл лога `{selected_log_path.name}` пуст (событий еще не зафиксировано).")
        except Exception as l_err:
            st.error(f"Ошибка чтения лога: {l_err}")
    else:
        st.caption(f"Файл лога `{selected_log_path.name}` еще не создан. Он появится при первом запуске операции.")

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

    # 3. Выполнить переиндексацию ChromaDB (с подробным консольным выводом):
    python reindex_rag.py --partial             # Быстрая переиндексация (только авто + новости)
    python reindex_rag.py                       # Полная переиндексация всех 5 коллекций

    # 4. Запустить нужный коллектор:
    python rag_collectors/runner.py --collector cars     # Ассортимент машин raskatof.ru
    python rag_collectors/runner.py --collector news     # Автоновости
    python rag_collectors/runner.py --collector pdd      # Правила дорожного движения РФ (ГИБДД PDF)
    python rag_collectors/runner.py --collector vsrf     # Судебная практика ВС РФ
    python rag_collectors/runner.py --collector laws     # ГК/НК/КоАП РФ в единый JSONL
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
