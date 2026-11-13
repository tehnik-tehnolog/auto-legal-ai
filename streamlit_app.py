"""
Streamlit Web-приложение для юридического RAG-ассистента компании по раскату машин в РФ.
Разделы боковой панели:
  1. 💬 RAG Ассистент (Чат) - с темами чатов, пиннингом, профилями юристов, прикреплением файлов (PDF/DOCX/TXT)
  2. 📜 Нормативная база (ГК/НК РФ) - с умной выборкой (список при >1 статьи, полная статья при 1)
  3. 🚦 Правила дорожного движения (ПДД РФ)
"""

import io
import json
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from rag_pipeline.chat_manager import DEFAULT_USERS, ChatManager
from rag_pipeline.config import (
    GEMINI_API_KEY,
    LEGAL_CHAPTERS_FILE,
    LEGAL_DIR,
    LEGAL_JSONL_FILE,
    LOGS_DIR,
    MODEL_NAME,
    PDD_CHAPTERS_FILE,
    PDD_DIR,
    PDD_RULES_FILE,
)
from rag_pipeline.generator import RAGAssistant, SYSTEM_PROMPT

# Настройка страницы Streamlit
st.set_page_config(
    page_title="Юридический RAG Ассистент | Раскат Авто РФ",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Глобальный реестр фоновых задач генерации (для непрерывности при переходах по разделам)
if "GLOBAL_JOBS" not in st.session_state:
    st.session_state.GLOBAL_JOBS = {}
GLOBAL_JOBS = st.session_state.GLOBAL_JOBS


# --- ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ ПРИКРЕПЛЕННЫХ ФАЙЛОВ ---
def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Извлечение текстового содержимого из PDF, DOCX, TXT и MD файлов"""
    lower_name = filename.lower()
    try:
        if lower_name.endswith(".pdf"):
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    pages_text.append(f"--- Страница {idx + 1} ---\n{text}")
            return "\n\n".join(pages_text)

        elif lower_name.endswith(".docx"):
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)

        else:
            return file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"[Ошибка извлечения текста из файла {filename}: {e}]"


# --- ФОНОВЫЙ ПОТОК ГЕНЕРАЦИИ (НЕ ПРЕРЫВАЕТСЯ ПРИ СМЕНЕ СТРАНИЦ) ---
def _run_background_rag_task(job_id: str, query: str, attached_text: str, user_id: str, chat_id: str):
    """Фоновый воркер: двухэтапный поиск 10 статей + вызов Gemini"""
    try:
        GLOBAL_JOBS[job_id]["status"] = "retrieving"
        assistant = RAGAssistant()

        # 1. Сбор 10 первоисточников (5 стандартных + 5 из расширения тем через Gemini)
        ctx_data = assistant.prepare_10_sources_context(query, attached_doc_text=attached_text)
        sources = ctx_data["sources"]
        topics = ctx_data["topics"]
        user_prompt = ctx_data["user_prompt"]
        targets = ctx_data.get("target_collections", [])

        GLOBAL_JOBS[job_id]["status"] = "generating"
        GLOBAL_JOBS[job_id]["sources"] = sources
        GLOBAL_JOBS[job_id]["topics"] = topics
        GLOBAL_JOBS[job_id]["targets"] = targets

        # 2. Обращение к Gemini на стороне Streamlit (отправка промпта)
        answer_text = ""
        fallback_used = False
        fallback_reason = None
        gemini_status = "ok"

        # Проверка и вызов клиента Google GenAI
        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=user_prompt,
                    config={
                        "system_instruction": SYSTEM_PROMPT,
                        "temperature": 0.2,
                    }
                )
                answer_text = response.text or ""
            except Exception as gemini_err:
                fallback_reason = f"Ошибка Gemini API ({type(gemini_err).__name__}): {gemini_err}"
                gemini_status = "error"
        else:
            fallback_reason = "GEMINI_API_KEY не задан в переменных окружения или файле .env"
            gemini_status = "missing_key"

        if not answer_text:
            fallback_used = True
            answer_text = assistant._extractive_fallback_generation(query, sources, reason=fallback_reason)

        GLOBAL_JOBS[job_id]["result"] = {
            "answer": answer_text,
            "sources": sources,
            "topics": topics,
            "targets": targets,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "gemini_status": gemini_status,
        }
        GLOBAL_JOBS[job_id]["status"] = "completed"

    except Exception as fatal_err:
        GLOBAL_JOBS[job_id]["status"] = "error"
        GLOBAL_JOBS[job_id]["error"] = str(fatal_err)


# --- ФУНКЦИИ ЗАГРУЗКИ НОРМ И ПДД ---
@st.cache_data(ttl=60)
def load_legal_chapters():
    docs = []
    target = LEGAL_CHAPTERS_FILE if LEGAL_CHAPTERS_FILE.exists() else LEGAL_JSONL_FILE
    if target.exists():
        try:
            with open(target, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        docs.append(json.loads(line))
        except Exception as e:
            st.error(f"Ошибка чтения legal_chapters.jsonl: {e}")
    return docs


@st.cache_data(ttl=60)
def load_pdd_chapters():
    chapters = []
    if PDD_CHAPTERS_FILE.exists():
        try:
            with open(PDD_CHAPTERS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        chapters.append(json.loads(line))
        except Exception as e:
            st.error(f"Ошибка чтения pdd_chapters.jsonl: {e}")
    return chapters


# --- ОБРАБОТКА URL QUERY PARAMETERS (?doc=... или ?pdd=...) ---
# Решает проблему прямых ссылок из чата и браузера
query_params = st.query_params

if "doc" in query_params:
    raw_doc_id = str(query_params.get("doc", "")).strip()
    clean_doc_id = re.sub(r'^(?:#?doc-legal_|#?legal_|#)', '', raw_doc_id)
    if clean_doc_id:
        st.session_state.app_sidebar_radio = "📜 Нормативная база (ГК/НК РФ)"
        st.session_state.current_nav = "📜 Нормативная база (ГК/НК РФ)"
        st.session_state.active_legal_doc_id = clean_doc_id

if "pdd" in query_params:
    raw_pdd_id = str(query_params.get("pdd", "")).strip()
    clean_pdd_id = re.sub(r'^(?:#?doc-pdd_|#?pdd_|#)', '', raw_pdd_id)
    if clean_pdd_id:
        st.session_state.app_sidebar_radio = "🚦 Правила дорожного движения (ПДД РФ)"
        st.session_state.current_nav = "🚦 Правила дорожного движения (ПДД РФ)"
        st.session_state.active_pdd_doc_id = clean_pdd_id


# --- УПРАВЛЕНИЕ ПРОФИЛЕМ ПОЛЬЗОВАТЕЛЯ И ТЕМАМИ ЧАТОВ ---
if "current_user_id" not in st.session_state:
    st.session_state.current_user_id = DEFAULT_USERS[0]["user_id"]

current_user_id = st.session_state.current_user_id
user_profile = ChatManager.load_user_profile(current_user_id)
active_chat = ChatManager.get_active_chat(user_profile)


# --- SIDEBAR: ТОЛЬКО 3 РАЗДЕЛА + ТЕМЫ ЧАТОВ И ПИННИНГ ---
with st.sidebar:
    st.title("⚖️ Раскат Авто РФ")
    st.caption("Юридический RAG-ассистент и нормативная база")

    # 1. Выбор профиля юриста
    user_options = {u["user_id"]: u["user_name"] for u in DEFAULT_USERS}
    selected_u_id = st.selectbox(
        "👤 Юрист (профиль):",
        options=list(user_options.keys()),
        format_func=lambda uid: user_options.get(uid, uid),
        index=list(user_options.keys()).index(current_user_id) if current_user_id in user_options else 0,
        key="sidebar_user_selector"
    )
    if selected_u_id != current_user_id:
        st.session_state.current_user_id = selected_u_id
        st.rerun()

    st.divider()

    # 2. Навигация (ОСТАВЛЕНЫ ТОЛЬКО 3 РАЗДЕЛА)
    nav_options = [
        "💬 RAG Ассистент (Чат)",
        "📜 Нормативная база (ГК/НК РФ)",
        "🚦 Правила дорожного движения (ПДД РФ)",
    ]

    if "current_nav" not in st.session_state:
        st.session_state.current_nav = "💬 RAG Ассистент (Чат)"

    try:
        radio_idx = nav_options.index(st.session_state.current_nav)
    except ValueError:
        radio_idx = 0

    selected_view = st.radio(
        "Раздел:",
        nav_options,
        index=radio_idx,
        key="app_sidebar_radio"
    )
    st.session_state.current_nav = selected_view

    st.divider()

    # 3. Управление темами чатов
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("📁 Темы чатов")
    with col_t2:
        if st.button("➕", help="Создать новый чат", key="btn_create_chat"):
            new_c_id = ChatManager.create_new_chat(user_profile)
            st.rerun()

    all_chats = user_profile.get("chats", [])
    pinned_chats = [c for c in all_chats if c.get("pinned", False)]
    recent_chats = [c for c in all_chats if not c.get("pinned", False)]

    # Закрепленные чаты (Pinned)
    if pinned_chats:
        st.caption("📌 Закрепленные чаты:")
        for c in pinned_chats:
            c_id = c["chat_id"]
            is_active = (c_id == user_profile.get("active_chat_id"))
            label = f"📌 {c['title']}"
            cols = st.columns([5, 1, 1])
            with cols[0]:
                btn_type = "primary" if is_active else "secondary"
                if st.button(label, key=f"chat_btn_{c_id}", use_container_width=True, type=btn_type):
                    user_profile["active_chat_id"] = c_id
                    ChatManager.save_user_profile(user_profile)
                    st.rerun()
            with cols[1]:
                if st.button("📍", help="Открепить чат", key=f"unpin_{c_id}"):
                    ChatManager.toggle_pin(user_profile, c_id)
                    st.rerun()
            with cols[2]:
                if st.button("🗑️", help="Удалить чат", key=f"del_pin_{c_id}"):
                    ChatManager.delete_chat(user_profile, c_id)
                    st.rerun()

    # Обычные темы чатов
    st.caption("🕒 Недавние диалоги:")
    for c in recent_chats[:8]:
        c_id = c["chat_id"]
        is_active = (c_id == user_profile.get("active_chat_id"))
        cols = st.columns([5, 1, 1])
        with cols[0]:
            btn_type = "primary" if is_active else "secondary"
            if st.button(c['title'], key=f"chat_btn_{c_id}", use_container_width=True, type=btn_type):
                user_profile["active_chat_id"] = c_id
                ChatManager.save_user_profile(user_profile)
                st.rerun()
        with cols[1]:
            if st.button("📌", help="Закрепить чат", key=f"pin_{c_id}"):
                ChatManager.toggle_pin(user_profile, c_id)
                st.rerun()
        with cols[2]:
            if st.button("🗑️", help="Удалить чат", key=f"del_{c_id}"):
                ChatManager.delete_chat(user_profile, c_id)
                st.rerun()

    st.divider()

    # Статистика базы
    legal_chapters = load_legal_chapters()
    pdd_chapters = load_pdd_chapters()
    tax_cnt = sum(1 for d in legal_chapters if "НК" in str(d.get("code", "")) or "tax" in str(d.get("parent_id", "")))
    civics_cnt = sum(1 for d in legal_chapters if "ГК" in str(d.get("code", "")) or "civics" in str(d.get("parent_id", "")))
    st.caption(f"📚 В базе: **{len(legal_chapters)}** статей (ГК: {civics_cnt}, НК: {tax_cnt}) | **{len(pdd_chapters)}** глав ПДД")


# ==============================================================================
# VIEW 1: ЧАТ RAG-АССИСТЕНТА С ПРИКРЕПЛЕНИЕМ ФАЙЛОВ И ДВУХЭТАПНЫМ ПОИСКОМ
# ==============================================================================
if selected_view == "💬 RAG Ассистент (Чат)":
    st.header(f"💬 {active_chat.get('title', 'Чат RAG-ассистента')}")
    st.caption("Конвейер: Вопрос ➔ Gemini (2-6 тем) ➔ Поиск ~40 статей ➔ Реранкинг ➔ 10 первоисточников ➔ Ответ")

    # Отображение истории сообщений активного чата
    messages = active_chat.get("messages", [])

    for msg in messages:
        with st.chat_message(msg["role"]):
            if msg.get("topics"):
                st.caption(f"🔎 **Выделенные темы вопроса (Gemini):** {' • '.join([f'`{t}`' for t in msg['topics']])}")

            if msg.get("targets"):
                target_labels = {
                    "legal_laws": "📜 Законы (ГК/НК РФ)",
                    "court_cases": "⚖️ ВС РФ (Судебная практика)",
                    "auto_news": "📰 Автоновости и рынок",
                    "traffic_rules": "🚦 ПДД РФ"
                }
                badges = [target_labels.get(t, t) for t in msg["targets"]]
                st.caption(f"🎯 **Коллекции поиска:** {' • '.join(badges)}")

            if msg.get("attached_filename"):
                st.info(f"📎 **Прикрепленный документ:** `{msg['attached_filename']}` ({msg.get('attached_chars', 0)} знаков)")

            if msg.get("fallback_used"):
                with st.expander("ℹ️ Статус подключения Gemini (загружен локальный генератор)"):
                    st.warning(f"Причина вызова локального синтеза: **{msg.get('fallback_reason')}**")
                    st.caption("Подробный лог сохранен в: `logs/gemini_connection.log`")

            st.markdown(msg["content"])

            if msg.get("sources"):
                with st.expander(f"📚 Использованные первоисточники (10 документов): 5 базовых + 5 тематических"):
                    for s_idx, s in enumerate(msg["sources"]):
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            tag_badge = "🌟 [Тематическое расширение]" if s.get("source_tag") == "topic_expansion" else "📌 [Базовый поиск]"
                            st.markdown(f"**[{s['title']}]({s['url']})** {tag_badge}")
                            if s.get("case_number"):
                                st.caption(f"Дело №: {s['case_number']} | Дата: {s.get('date', 'Не указана')}")
                            st.text(f"Фрагмент: {s['matched_chunk'][:240]}...")

                            # Кнопка мгновенного перехода в просмотрщик статей
                            coll = s.get("collection", "")
                            doc_t = s.get("doc_type", "")
                            p_id = s.get("parent_id")
                            if (coll == "legal_laws" or doc_t == "legal_law") and p_id:
                                if st.button(f"📖 Открыть статью в просмотрщике", key=f"hist_legal_{p_id}_{s_idx}"):
                                    st.session_state.app_sidebar_radio = "📜 Нормативная база (ГК/НК РФ)"
                                    st.session_state.current_nav = "📜 Нормативная база (ГК/НК РФ)"
                                    st.session_state.active_legal_doc_id = p_id
                                    st.query_params["doc"] = p_id
                                    st.rerun()
                            elif (coll == "traffic_rules" or doc_t == "traffic_rules") and p_id:
                                if st.button(f"🚦 Открыть главу ПДД в просмотрщике", key=f"hist_pdd_{p_id}_{s_idx}"):
                                    st.session_state.app_sidebar_radio = "🚦 Правила дорожного движения (ПДД РФ)"
                                    st.session_state.current_nav = "🚦 Правила дорожного движения (ПДД РФ)"
                                    st.session_state.active_pdd_doc_id = p_id
                                    st.query_params["pdd"] = p_id
                                    st.rerun()

                        with col_b:
                            st.metric("Rerank Score", f"{s.get('similarity_score', 0.0):.3f}")
                        st.divider()

    # Проверка активного фонового задания генерации (не прерывается при переходах)
    active_job_id = st.session_state.get("active_job_id")
    if active_job_id and active_job_id in GLOBAL_JOBS:
        job_info = GLOBAL_JOBS[active_job_id]
        status = job_info.get("status")

        if status in ("retrieving", "generating"):
            with st.chat_message("assistant"):
                st.info("⏳ **Формирование ответа в фоновом режиме...** Идет выделение тем и отбор 10 статей.")
                with st.spinner("Конвейер работает в фоне (вы можете переходить в разделы 'Нормативная база' и 'ПДД')..."):
                    time.sleep(2)
                    st.rerun()

        elif status == "completed":
            res = job_info.get("result", {})
            new_msg = {
                "role": "assistant",
                "content": res.get("answer", ""),
                "sources": res.get("sources", []),
                "topics": res.get("topics", []),
                "targets": res.get("targets", []),
                "fallback_used": res.get("fallback_used", False),
                "fallback_reason": res.get("fallback_reason")
            }
            active_chat["messages"].append(new_msg)
            # Обновляем заголовок чата, если он стандартный
            if "Новый диалог" in active_chat.get("title", "") and res.get("topics"):
                active_chat["title"] = f"{res['topics'][0].capitalize()}"
            ChatManager.save_user_profile(user_profile)
            st.session_state.active_job_id = None
            st.rerun()

        elif status == "error":
            st.error(f"Ошибка фонового конвейера: {job_info.get('error')}")
            st.session_state.active_job_id = None

    # Поле загрузки файла (PDF, DOCX, TXT)
    with st.expander("📎 Прикрепить документ юриста к вопросу (PDF, DOCX, TXT)", expanded=False):
        uploaded_file = st.file_uploader(
            "Выберите файл договора, иска, акта или претензии:",
            type=["pdf", "docx", "txt", "md"],
            key="chat_file_attachment"
        )
        if uploaded_file:
            st.caption(f"Файл: `{uploaded_file.name}` ({uploaded_file.size / 1024:.1f} КБ)")

    # Ввод вопроса
    if prompt := st.chat_input("Задайте правовой вопрос по аренде с выкупом, налогам или ПДД..."):
        file_text = ""
        file_name = None
        if uploaded_file:
            file_name = uploaded_file.name
            file_text = extract_text_from_file(uploaded_file.getvalue(), file_name)

        user_entry = {
            "role": "user",
            "content": prompt,
            "attached_filename": file_name,
            "attached_chars": len(file_text) if file_text else 0
        }
        active_chat["messages"].append(user_entry)
        ChatManager.save_user_profile(user_profile)

        # Создаем фоновую задачу
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        GLOBAL_JOBS[job_id] = {
            "status": "started",
            "user_id": current_user_id,
            "chat_id": active_chat.get("chat_id"),
            "result": None,
            "error": None
        }
        st.session_state.active_job_id = job_id

        # Запуск в фоновом потоке
        t = threading.Thread(
            target=_run_background_rag_task,
            args=(job_id, prompt, file_text, current_user_id, active_chat.get("chat_id")),
            daemon=True
        )
        t.start()
        st.rerun()


# ==============================================================================
# VIEW 2: НОРМАТИВНАЯ БАЗА (ГК/НК РФ) С УМНОЙ ВЫБОРКОЙ
# ==============================================================================
elif selected_view == "📜 Нормативная база (ГК/НК РФ)":
    st.header("📜 Нормативно-правовая база (ГК РФ / НК РФ / КоАП РФ / Лизинг)")
    st.caption("Структурированное хранение по статьям: `data/legal/legal_chapters.jsonl`")

    legal_items = load_legal_chapters()

    if not legal_items:
        st.info("Нормативные акты будут загружены в `data/legal/legal_chapters.jsonl`.")
    else:
        # Фильтры: Кодекс / Закон, Категория, Поиск
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        all_codes = sorted(list(set(d.get("code", d.get("section", "ГК РФ")) for d in legal_items if d.get("code") or d.get("section"))))
        with col_f1:
            selected_code = st.selectbox("Кодекс / Закон:", ["Все акты"] + all_codes)
        with col_f2:
            all_cats = sorted(list(set(d.get("category", "") for d in legal_items if d.get("category"))))
            selected_cat = st.selectbox("Категория (тема):", ["Все категории"] + all_cats)
        with col_f3:
            search_query = st.text_input("Поиск по номеру статьи, главе или термину (например 615, лизинг, налог):", "")

        filtered_docs = legal_items
        if selected_code != "Все акты":
            filtered_docs = [d for d in filtered_docs if (d.get("code") == selected_code or d.get("section") == selected_code)]
        if selected_cat != "Все категории":
            filtered_docs = [d for d in filtered_docs if d.get("category") == selected_cat]
        if search_query.strip():
            sq = search_query.lower()
            filtered_docs = [
                d for d in filtered_docs
                if sq in d.get("title", "").lower()
                or sq in d.get("chapter_number", "").lower()
                or sq in d.get("article_number", "").lower()
                or sq in d.get("body", "").lower()
                or sq in d.get("parent_id", "").lower()
            ]

        # Проверка активного документа (выбранного по кнопке, ссылке или из списка)
        active_id = st.session_state.get("active_legal_doc_id")
        active_doc = None
        if active_id:
            active_doc = next((d for d in legal_items if d.get("parent_id") == active_id or d.get("doc_id") == active_id), None)

        # ТРЕБОВАНИЕ: Если статей больше 1 — выводить только Список всех статей выборки.
        # Если статья 1 (или выбрана конкретная статья) — показывать полный текст статьи.
        if active_doc:
            col_back, _ = st.columns([1, 4])
            with col_back:
                if st.button("← Вернуться к списку выборки", key="btn_back_to_list"):
                    st.session_state.active_legal_doc_id = None
                    if "doc" in st.query_params:
                        del st.query_params["doc"]
                    st.rerun()

            with st.container(border=True):
                st.markdown(f'<a id="doc-legal_{active_doc.get("parent_id")}"></a>', unsafe_allow_html=True)
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.subheader(f"📖 {active_doc.get('title')}")
                    st.caption(f"📁 {active_doc.get('code', 'ГК РФ')} | {active_doc.get('chapter_number', '')} | Тема: **{active_doc.get('category', 'Законодательство')}**")
                with col_h2:
                    p_lvl = active_doc.get("priority_level", "standard").upper()
                    st.caption(f"Приоритет: `{p_lvl}`")
                    st.markdown(f"[🌐 Первоисточник (docs.cntd.ru)]({active_doc.get('original_url', 'https://docs.cntd.ru')})")

                st.divider()
                st.markdown(active_doc.get("body", active_doc.get("full_text", "")))
                if active_doc.get("details"):
                    st.caption(f"Реквизиты: {active_doc.get('details')}")

        elif len(filtered_docs) == 1:
            single_doc = filtered_docs[0]
            with st.container(border=True):
                st.markdown(f'<a id="doc-legal_{single_doc.get("parent_id")}"></a>', unsafe_allow_html=True)
                col_h1, col_h2 = st.columns([3, 1])
                with col_h1:
                    st.subheader(f"📖 {single_doc.get('title')}")
                    st.caption(f"📁 {single_doc.get('code', 'ГК РФ')} | {single_doc.get('chapter_number', '')} | Тема: **{single_doc.get('category', 'Законодательство')}**")
                with col_h2:
                    p_lvl = single_doc.get("priority_level", "standard").upper()
                    st.caption(f"Приоритет: `{p_lvl}`")
                    st.markdown(f"[🌐 Первоисточник (docs.cntd.ru)]({single_doc.get('original_url', 'https://docs.cntd.ru')})")

                st.divider()
                st.markdown(single_doc.get("body", single_doc.get("full_text", "")))
                if single_doc.get("details"):
                    st.caption(f"Реквизиты: {single_doc.get('details')}")

        elif len(filtered_docs) > 1:
            st.info(f"📋 **Список всех статей выборки:** Найдено **{len(filtered_docs)}** статей. Выберите статью для чтения:")

            # Таблица / карточки списка выборки
            for idx, doc in enumerate(filtered_docs):
                p_id = doc.get("parent_id", f"doc_{idx}")
                with st.container(border=True):
                    c1, c2, c3 = st.columns([4, 2, 1])
                    with c1:
                        st.markdown(f"**{doc.get('title')}**")
                        st.caption(f"Раздел: `{doc.get('chapter_number', '')}` | ID: `{p_id}`")
                    with c2:
                        st.caption(f"Тема: **{doc.get('category', '')}**")
                        st.caption(f"Кодекс: `{doc.get('code', '')}`")
                    with c3:
                        if st.button("📖 Читать", key=f"open_art_{p_id}_{idx}", use_container_width=True):
                            st.session_state.active_legal_doc_id = p_id
                            st.query_params["doc"] = p_id
                            st.rerun()

        else:
            st.warning("По заданным фильтрам статей не найдено. Попробуйте изменить параметры поиска.")


# ==============================================================================
# VIEW 3: ПРАВИЛА ДОРОЖНОГО ДВИЖЕНИЯ (ПДД РФ)
# ==============================================================================
elif selected_view == "🚦 Правила дорожного движения (ПДД РФ)":
    st.header("🚦 Правила дорожного движения РФ (ПДД РФ)")
    st.caption("Структурированное хранение по главам: `data/pdd/pdd_chapters.jsonl`")

    pdd_items = load_pdd_chapters()

    if not pdd_items:
        st.warning("Файл ПДД не найден в `data/pdd/pdd_chapters.jsonl`.")
    else:
        active_pdd_id = st.session_state.get("active_pdd_doc_id")
        active_ch = next((c for c in pdd_items if c.get("parent_id") == active_pdd_id or c.get("doc_id") == active_pdd_id), None)

        ch_options = [f"{c.get('chapter_number', '')}: {c.get('chapter_title', c.get('title', ''))}" for c in pdd_items]
        def_pdd_idx = 0
        if active_ch and active_ch in pdd_items:
            def_pdd_idx = pdd_items.index(active_ch)

        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            selected_ch_label = st.selectbox("Выберите главу или раздел ПДД РФ:", ch_options, index=def_pdd_idx)
        with col_p2:
            st.metric("Глав и разделов", len(pdd_items), delta="Действующая редакция РФ")

        sel_pdd_idx = ch_options.index(selected_ch_label)
        cur_ch = pdd_items[sel_pdd_idx]

        search_kw = st.text_input("Поиск по тексту выбранной главы (например скорость, обгон, тормоз):", "")

        with st.container(border=True):
            st.markdown(f'<a id="doc-pdd_{cur_ch.get("parent_id")}"></a>', unsafe_allow_html=True)
            st.subheader(f"🚦 {cur_ch.get('title')}")
            st.caption(f"📁 {cur_ch.get('chapter_number', '')} | ID: `{cur_ch.get('parent_id')}`")
            st.divider()

            ch_body = cur_ch.get("body", cur_ch.get("full_text", ""))
            if search_kw.strip():
                kw = search_kw.lower()
                highlighted_lines = []
                for line in ch_body.split("\n"):
                    if kw in line.lower():
                        highlighted_lines.append(f"👉 **{line.strip()}**")
                    else:
                        highlighted_lines.append(line)
                st.markdown("\n".join(highlighted_lines))
            else:
                st.markdown(ch_body)

        with st.expander(f"📑 Полное оглавление Правил дорожного движения ({len(pdd_items)} разделов)"):
            for ch in pdd_items:
                ch_pid = ch.get("parent_id", "")
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{ch.get('chapter_number', '')}**: {ch.get('chapter_title', '')}")
                if c2.button("Перейти", key=f"nav_pdd_ch_{ch_pid}"):
                    st.session_state.active_pdd_doc_id = ch_pid
                    st.query_params["pdd"] = ch_pid
                    st.rerun()
