"""
Streamlit Web-приложение для юридического RAG-ассистента компании по раскату машин в РФ.
Готово к деплою на Render.com (Free Tier без локального диска, с пробуждением по WEBHOOK_BASE_URL):
  - Регистрация и вход пользователей по Email + Имени (хранение в Supabase PostgreSQL)
  - Хранение прикрепленных документов и синхронизация БЗ через Backblaze B2 Cloud Storage
  - 3 раздела боковой панели: Чат, Нормативная база (ГК/НК РФ), ПДД РФ
  - Двухэтапный поиск (10 статей с Gemini; строго 5 базовых фрагментов при сбое подключения к Gemini API)
"""

import io
import json
import logging
import os
import re
import threading
import time
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
import streamlit.components.v1 as components

from rag_pipeline.b2_storage import B2StorageManager
from rag_pipeline.chat_manager import ChatManager
from rag_pipeline.config import (
    DATA_DIR,
    GEMINI_API_KEY,
    LEGAL_CHAPTERS_FILE,
    LEGAL_JSONL_FILE,
    MODEL_NAME,
    PDD_CHAPTERS_FILE,
    WEBHOOK_BASE_URL,
)
from rag_pipeline.db_supabase import SupabaseChatDB
from rag_pipeline.generator import RAGAssistant, SYSTEM_PROMPT
from rag_pipeline.ui_icons import build_ui_icons_css, detect_streamlit_theme, icon_img_html

logger = logging.getLogger("streamlit_app")

# Настройка страницы Streamlit
st.set_page_config(
    page_title="Юридический Ассистент для РФ",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": None,
    },
)

# Определение темы и кэшированное подключение пользовательских SVG-иконок
@st.cache_data(ttl=300)
def _get_cached_ui_css(theme: Optional[str]) -> str:
    return build_ui_icons_css(theme)


ACTIVE_THEME = detect_streamlit_theme(st)
st.markdown(_get_cached_ui_css(ACTIVE_THEME), unsafe_allow_html=True)

# --- ГЛОБАЛЬНЫЙ CSS ---
st.markdown(
    """
    <style>
    /* 1. Компактный верх страницы */
    .block-container { padding-top: 1.5rem !important; }

    /* 2. Скрыть кнопку Deploy */
    [data-testid="stAppDeployButton"],
    [data-testid="stDeployButton"] { display: none !important; }

    /* 3. Убрать «Press Enter to apply» везде (auth-страница, поиск в selectbox и т. п.) */
    [data-testid="InputInstructions"],
    [data-testid="stTextInputRootElement"] small,
    [data-testid="stTextAreaRootElement"] small,
    [data-testid="stNumberInputRootElement"] small,
    .stSelectbox small { display: none !important; }

    /* 4. Убрать anchor-значки у заголовков */
    [data-testid="stHeaderActionElements"] { display: none !important; }
    .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a,
    .stMarkdown h4 a, .stMarkdown h5 a, .stMarkdown h6 a { display: none !important; }

    /* 5. Скрепка вместо «Browse files» в file_uploader */
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    [data-testid="stFileUploaderDropzone"] {
        min-height: auto !important;
        padding: 0.15rem !important;
        border: none !important;
        background: transparent !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        font-size: 0 !important;
        line-height: 0 !important;
        padding: 0.35rem 0.55rem !important;
        min-height: 2.2rem !important;
        min-width: 2.4rem !important;
        border: none !important;
        background: transparent !important;
    }
    [data-testid="stFileUploaderDropzone"] button > * { display: none !important; }
    [data-testid="stFileUploaderDropzone"] button::after {
        content: "📎";
        font-size: 1.35rem;
        line-height: 1;
        display: inline-block;
        visibility: visible;
    }

    /* 5b. Закрепленная нижняя панель ввода без приватного st._bottom */
    [data-testid="stHorizontalBlock"]:has([data-testid="stChatInput"]) {
        position: sticky;
        bottom: 0;
        z-index: 90;
        background: var(--background-color, var(--default-backgroundColor, inherit));
        padding: 0.45rem 0 0.75rem 0;
        border-top: 1px solid rgba(128, 128, 128, 0.14);
    }

    /* 6. Компактный сайдбар */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
        margin-bottom: 0.05rem !important;
    }
    [data-testid="stSidebar"] hr { margin: 0.3rem 0 !important; }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] { align-items: center !important; }
    [data-testid="stSidebar"] .stButton button {
        min-height: 1.8rem !important;
        padding: 0.12rem 0.35rem !important;
        margin: 0 !important;
    }

    /* 7. Профиль без рамок */
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        border: none !important;
        padding: 0 !important;
    }

    /* 8. Строка темы чата: 4 колонки [text, pin/unpin, rename, remove] */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) {
        gap: 0 !important;
        margin-bottom: 0.1rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) > div {
        padding: 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) [data-testid="stButton"] button {
        border: none !important;
        background: transparent !important;
        padding: 0.1rem !important;
        min-height: 1.75rem !important;
        font-size: 0.95rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }
    /* pin / unpin — ВСЕГДА ВИДИМЫ, крупнее, по центру */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) > div:nth-child(2) [data-testid="stButton"] button {
        opacity: 1 !important;
        font-size: 1.2rem !important;
        text-align: center !important;
        justify-content: center !important;
    }
    /* rename / remove — только по наведению */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) > div:nth-child(3) [data-testid="stButton"] button,
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> div:nth-child(4)) > div:nth-child(4) [data-testid="stButton"] button {
        opacity: 0 !important;
        transition: opacity 0.15s ease !important;
        font-size: 1.2rem !important;
        text-align: center !important;
        justify-content: center !important;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> div:nth-child(4)):hover > div:nth-child(3) [data-testid="stButton"] button,
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(> div:nth-child(4)):hover > div:nth-child(4) [data-testid="stButton"] button {
        opacity: 1 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Одноразовая инъекция JS-хуков на сессию (без MutationObserver на document.body)
def inject_session_js_hooks_once():
    if st.session_state.get("_js_hooks_injected"):
        return
    st.session_state._js_hooks_injected = True

    wake_js = ""
    if WEBHOOK_BASE_URL:
        safe_url = json.dumps(f"{WEBHOOK_BASE_URL}/_stcore/health")
        wake_js = f"""
        const wakeUrl = {safe_url};
        if (!w.__renderWakeBound) {{
            w.__renderWakeBound = true;
            w.document.addEventListener("visibilitychange", function() {{
                if (w.document.visibilityState === "visible") {{
                    w.fetch(wakeUrl, {{ mode: "no-cors", cache: "no-store" }}).catch(() => {{}});
                }}
            }});
        }}
        """

    components.html(
        f"""
        <script>
        (function() {{
            try {{
                const w = window.parent;
                const doc = w.document;
                const WANTED = ["settings"];
                function cleanMenu() {{
                    const menu = doc.querySelector('[data-testid="stMainMenu"]');
                    if (!menu) return;
                    menu.querySelectorAll('li').forEach(function(li) {{
                        const txt = (li.textContent || '').trim().toLowerCase();
                        const keep = WANTED.some(function(wKey) {{ return txt.includes(wKey); }});
                        if (!keep) li.style.display = 'none';
                    }});
                }}
                if (!w.__menuCleanBound) {{
                    w.__menuCleanBound = true;
                    setTimeout(cleanMenu, 300);
                    doc.addEventListener('click', function(e) {{
                        if (e.target && e.target.closest && e.target.closest('[data-testid="stMainMenu"]')) {{
                            setTimeout(cleanMenu, 60);
                        }}
                    }}, true);
                }}
                {wake_js}
            }} catch (e) {{}}
        }})();
        </script>
        """,
        height=0,
    )


inject_session_js_hooks_once()

# Глобальный реестр фоновых задач
if "GLOBAL_JOBS" not in st.session_state:
    st.session_state.GLOBAL_JOBS = {}
GLOBAL_JOBS = st.session_state.GLOBAL_JOBS


# --- ИНИЦИАЛИЗАЦИЯ ОБЛАЧНЫХ РЕСУРСОВ ---
@st.cache_resource
def bootstrap_cloud_and_rag() -> Dict[str, Any]:
    db_ok = SupabaseChatDB.init_schema() if SupabaseChatDB.is_configured() else False
    b2_sync = {"configured": B2StorageManager.is_configured(), "downloaded": 0}
    if B2StorageManager.is_configured() and (not LEGAL_CHAPTERS_FILE.exists() or not PDD_CHAPTERS_FILE.exists()):
        b2_sync = B2StorageManager.sync_kb_from_b2(DATA_DIR)
    assistant = RAGAssistant()
    return {"db_ok": db_ok, "b2_sync": b2_sync, "assistant": assistant}


CLOUD_BOOT = bootstrap_cloud_and_rag()


def get_rag_assistant() -> RAGAssistant:
    return CLOUD_BOOT["assistant"]


# --- ПРОБУЖДЕНИЕ RENDER ---
def trigger_render_wakeup():
    if not WEBHOOK_BASE_URL:
        return

    def _ping():
        for suffix in ("/_stcore/health", "/"):
            try:
                requests.get(f"{WEBHOOK_BASE_URL}{suffix}", timeout=8)
                break
            except Exception:
                continue

    threading.Thread(target=_ping, daemon=True).start()


# --- ИЗВЛЕЧЕНИЕ ТЕКСТА ---
def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
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


# --- ФОНОВЫЙ ПОТОК ГЕНЕРАЦИИ ---
def _run_background_rag_task(
    job_id: str, query: str, attached_text: str, user_email: str, chat_id: str, assistant: RAGAssistant,
):
    try:
        GLOBAL_JOBS[job_id]["status"] = "retrieving"
        ctx_data = assistant.prepare_10_sources_context(query, attached_doc_text=attached_text)
        sources = ctx_data["sources"]
        topics = ctx_data["topics"]
        user_prompt = ctx_data["user_prompt"]
        targets = ctx_data.get("target_collections", [])
        gemini_connected = ctx_data.get("gemini_connected", False)

        GLOBAL_JOBS[job_id]["status"] = "generating"
        GLOBAL_JOBS[job_id]["sources"] = sources
        GLOBAL_JOBS[job_id]["topics"] = topics
        GLOBAL_JOBS[job_id]["targets"] = targets

        answer_text = ""
        fallback_used = False
        fallback_reason = None
        gemini_status = "ok"

        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=user_prompt,
                    config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.2},
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
            if not fallback_reason:
                fallback_reason = "Пустой ответ от Gemini API"
            sources = [s for s in sources if s.get("source_tag") == "standard_retrieval"][:5] or sources[:5]
            topics = []
            answer_text = assistant._extractive_fallback_generation(query, sources, reason=fallback_reason)
        elif not gemini_connected:
            sources = sources[:5]

        result_payload = {
            "answer": answer_text,
            "sources": sources,
            "topics": topics,
            "targets": targets,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "gemini_status": gemini_status,
        }

        saved_in_db = False
        if ChatManager.is_cloud_db_active():
            msg_record = {
                "role": "assistant",
                "content": answer_text,
                "sources": sources,
                "topics": topics,
                "targets": targets,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
            }
            saved_in_db = SupabaseChatDB.append_message(chat_id, msg_record)

        GLOBAL_JOBS[job_id]["saved_in_db"] = saved_in_db
        GLOBAL_JOBS[job_id]["result"] = result_payload
        GLOBAL_JOBS[job_id]["status"] = "completed"

    except Exception as fatal_err:
        GLOBAL_JOBS[job_id]["status"] = "error"
        GLOBAL_JOBS[job_id]["error"] = str(fatal_err)


# --- ЗАГРУЗКА БАЗ И КЭШИРОВАНИЕ ПРОФИЛЯ ---
@st.cache_data(ttl=3600)
def load_legal_chapters() -> List[Dict[str, Any]]:
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


@st.cache_data(ttl=3600)
def load_pdd_chapters() -> List[Dict[str, Any]]:
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


@st.cache_data(ttl=3600)
def _get_kb_stats() -> Dict[str, int]:
    legal = load_legal_chapters()
    pdd = load_pdd_chapters()
    tax_cnt = sum(1 for d in legal if "НК" in str(d.get("code", "")) or "tax" in str(d.get("parent_id", "")))
    civics_cnt = sum(1 for d in legal if "ГК" in str(d.get("code", "")) or "civics" in str(d.get("parent_id", "")))
    return {"legal": len(legal), "civics": civics_cnt, "tax": tax_cnt, "pdd": len(pdd)}


@st.cache_data(ttl=15)
def _cached_load_profile_meta(email: str, default_name: str) -> Dict[str, Any]:
    return ChatManager.load_profile_meta(email, default_name)


@st.cache_data(ttl=15)
def _cached_load_chat_messages(email: str, chat_id: str) -> List[Dict[str, Any]]:
    return ChatManager.load_chat_messages(email, chat_id)


@st.cache_data(ttl=30)
def _cached_list_known_users() -> List[Dict[str, str]]:
    return ChatManager.list_known_users()


def _invalidate_chat_caches():
    _cached_load_profile_meta.clear()
    _cached_load_chat_messages.clear()


def _set_query_param_if_changed(key: str, val: str):
    if st.query_params.get(key) != val:
        st.query_params[key] = val


def inject_user_into_internal_links(markdown_text: str, user_email: str) -> str:
    if not user_email or not markdown_text:
        return markdown_text
    enc_u = urllib.parse.quote(user_email, safe="")
    updated = re.sub(r"\?doc=([a-zA-Z0-9_.-]+)", rf"?u={enc_u}&doc=\1", markdown_text)
    updated = re.sub(r"\?pdd=([a-zA-Z0-9_.-]+)", rf"?u={enc_u}&pdd=\1", updated)
    return updated


# --- URL QUERY PARAMS ---
query_params = st.query_params

if "u" in query_params and not st.session_state.get("current_user_email"):
    raw_u = str(query_params.get("u", "")).strip().lower()
    if "@" in raw_u:
        st.session_state.current_user_email = raw_u

has_direct_doc_link = False
if "doc" in query_params:
    raw_doc_id = str(query_params.get("doc", "")).strip()
    clean_doc_id = re.sub(r"^(?:#?doc-legal_|#?legal_|#)", "", raw_doc_id)
    if clean_doc_id:
        st.session_state.current_nav = "📜 Нормативная база (ГК/НК РФ)"
        st.session_state.active_legal_doc_id = clean_doc_id
        has_direct_doc_link = True

if "pdd" in query_params:
    raw_pdd_id = str(query_params.get("pdd", "")).strip()
    clean_pdd_id = re.sub(r"^(?:#?doc-pdd_|#?pdd_|#)", "", raw_pdd_id)
    if clean_pdd_id:
        st.session_state.current_nav = "🚦 Правила дорожного движения (ПДД РФ)"
        st.session_state.active_pdd_doc_id = clean_pdd_id
        has_direct_doc_link = True


# --- ЭКРАН АВТОРИЗАЦИИ (со значком court) ---
def render_auth_gate():
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin:0 0 0.25rem 0;'>"
            f"{icon_img_html('court', size=34, theme=ACTIVE_THEME)}"
            f"<h1 style='margin:0;font-size:1.9rem;'>Юридический ассистент для РФ</h1>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption("Вход и регистрация")

        with st.container(border=True):
            # Поля без формы — Enter НЕ отправляет
            name_val = st.text_input("Имя", key="auth_name_field")
            email_val = st.text_input("Email", placeholder="lawyer@company.ru", key="auth_email_field")

            if st.button("Войти / Зарегистрироваться", type="primary", use_container_width=True):
                clean_email = email_val.strip().lower()
                clean_name = name_val.strip()
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
                    st.error("Пожалуйста, введите корректный адрес электронной почты (например: user@company.ru).")
                elif not clean_name:
                    st.error("Пожалуйста, введите ваше имя.")
                else:
                    profile = ChatManager.register_or_login(clean_email, clean_name)
                    _invalidate_chat_caches()
                    _cached_list_known_users.clear()
                    st.session_state.current_user_email = profile.get("email", clean_email)
                    st.session_state.current_user_name = profile.get("user_name", clean_name)
                    _set_query_param_if_changed("u", st.session_state.current_user_email)
                    st.rerun()

            # Только валидные записи (без плейсхолдерных «Юрист | Юрист | Юрист»)
            known_users = _cached_list_known_users() or []
            valid_users = [
                ku for ku in known_users
                if ku.get("user_name")
                and ku.get("user_name") != "Юрист"
                and (ku.get("email") or "").strip()
            ]
            if valid_users:
                st.divider()
                st.caption("Ранее входившие пользователи:")
                cols = st.columns(min(len(valid_users), 3))
                for idx, ku in enumerate(valid_users[:6]):
                    u_email = ku.get("email") or ku.get("user_id")
                    u_name = ku.get("user_name")
                    with cols[idx % len(cols)]:
                        if st.button(f"{u_name}", key=f"quick_login_{idx}_{u_email}", use_container_width=True):
                            st.session_state.current_user_email = u_email
                            st.session_state.current_user_name = u_name
                            _set_query_param_if_changed("u", u_email)
                            st.rerun()


if not st.session_state.get("current_user_email") and not has_direct_doc_link:
    render_auth_gate()
    st.stop()


current_user_email = st.session_state.get("current_user_email", "")
current_user_name = st.session_state.get("current_user_name", "")
user_profile: Optional[Dict[str, Any]] = None
active_chat: Optional[Dict[str, Any]] = None
active_chat_messages: List[Dict[str, Any]] = []

if current_user_email:
    user_profile = _cached_load_profile_meta(current_user_email, current_user_name or "Юрист")
    active_chat = ChatManager.get_active_chat(user_profile)
    active_chat_messages = _cached_load_chat_messages(current_user_email, active_chat.get("chat_id", ""))
    st.session_state.current_user_name = user_profile.get("user_name", current_user_name)

if "current_nav" not in st.session_state:
    st.session_state.current_nav = "💬 RAG Ассистент (Чат)"


# --- SIDEBAR ---
with st.sidebar:
    if user_profile:
        st.markdown(f"**{user_profile.get('user_name', 'Юрист')}**")
        st.caption(f"{user_profile.get('email', current_user_email)}")
        if st.button("Сменить пользователя / Выйти", key="btn_logout_user", use_container_width=True):
            st.session_state.pop("current_user_email", None)
            st.session_state.pop("current_user_name", None)
            st.session_state.pop("active_job_id", None)
            if "u" in st.query_params:
                del st.query_params["u"]
            st.rerun()
    else:
        if st.button("Войти / Зарегистрироваться", key="btn_guest_login", type="primary", use_container_width=True):
            if "doc" in st.query_params:
                del st.query_params["doc"]
            if "pdd" in st.query_params:
                del st.query_params["pdd"]
            st.rerun()

    st.divider()

    nav_items = [
        ("💬 RAG Ассистент (Чат)", "Ассистент (Чат)", "nav_btn_chat"),
        ("📜 Нормативная база (ГК/НК РФ)", "Нормативная база", "nav_btn_legal"),
        ("🚦 Правила дорожного движения (ПДД РФ)", "Правила дорожного движения", "nav_btn_pdd"),
    ]
    for nav_id, nav_label, btn_key in nav_items:
        is_current = st.session_state.current_nav == nav_id
        if st.button(
            nav_label,
            key=btn_key,
            type="primary" if is_current else "secondary",
            use_container_width=True,
        ):
            st.session_state.current_nav = nav_id
            st.rerun()

    selected_view = st.session_state.current_nav

    if user_profile:
        st.divider()
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.subheader("Темы чатов")
        with col_t2:
            if st.button("➕", help="Создать новый чат", key="btn_create_chat"):
                ChatManager.create_new_chat(user_profile)
                _invalidate_chat_caches()
                st.session_state.renaming_chat_id = None
                st.rerun()

        all_chats = user_profile.get("chats", [])
        pinned_chats = [c for c in all_chats if c.get("pinned", False)]
        recent_chats = [c for c in all_chats if not c.get("pinned", False)]

        def _render_chat_row(c: Dict[str, Any], is_pinned_section: bool):
            c_id = c["chat_id"]
            is_active = c_id == user_profile.get("active_chat_id")
            cols = st.columns([5.5, 0.8, 0.8, 0.8], gap="small")
            with cols[0]:
                btn_type = "primary" if is_active else "secondary"
                if st.button(c["title"], key=f"chat_btn_{c_id}", use_container_width=True, type=btn_type):
                    ChatManager.set_active_chat(user_profile, c_id)
                    _invalidate_chat_caches()
                    st.session_state.current_nav = "💬 RAG Ассистент (Чат)"
                    st.rerun()
            with cols[1]:
                if is_pinned_section:
                    if st.button(" ", help="Открепить чат", key=f"unpin_btn_{c_id}", use_container_width=True):
                        ChatManager.toggle_pin(user_profile, c_id)
                        _invalidate_chat_caches()
                        st.rerun()
                else:
                    if st.button(" ", help="Закрепить чат", key=f"pin_btn_{c_id}", use_container_width=True):
                        ChatManager.toggle_pin(user_profile, c_id)
                        _invalidate_chat_caches()
                        st.rerun()
            with cols[2]:
                if st.button(" ", help="Переименовать чат", key=f"rename_btn_{c_id}", use_container_width=True):
                    if st.session_state.get("renaming_chat_id") == c_id:
                        st.session_state.renaming_chat_id = None
                    else:
                        st.session_state.renaming_chat_id = c_id
                    st.rerun()
            with cols[3]:
                del_key = f"del_pin_btn_{c_id}" if is_pinned_section else f"del_btn_{c_id}"
                if st.button(" ", help="Удалить чат", key=del_key, use_container_width=True):
                    ChatManager.delete_chat(user_profile, c_id)
                    _invalidate_chat_caches()
                    st.rerun()

            if st.session_state.get("renaming_chat_id") == c_id:
                new_t = st.text_input("Новое название:", value=c["title"], key=f"rename_inp_{c_id}", label_visibility="collapsed")
                rc1, rc2 = st.columns(2)
                if rc1.button("Сохранить", key=f"save_ren_{c_id}", use_container_width=True):
                    ChatManager.rename_chat(user_profile, c_id, new_t)
                    _invalidate_chat_caches()
                    st.session_state.renaming_chat_id = None
                    st.rerun()
                if rc2.button("Отмена", key=f"canc_ren_{c_id}", use_container_width=True):
                    st.session_state.renaming_chat_id = None
                    st.rerun()

        for c in pinned_chats:
            _render_chat_row(c, is_pinned_section=True)
        for c in recent_chats[:10]:
            _render_chat_row(c, is_pinned_section=False)

    st.divider()

    kb_stats = _get_kb_stats()
    st.caption(f"В базе: **{kb_stats['legal']}** статей (ГК: {kb_stats['civics']}, НК: {kb_stats['tax']}) | **{kb_stats['pdd']}** глав ПДД")


# Приветствие ассистента
NEW_GREETING = (
    "Здравствуйте. Я юридический ассистент.\n\n"
    "Готов проанализировать правовые вопросы по аренде с выкупом, лизингу, "
    "учету расходов, налогам (НК РФ), судебной практике ВС РФ и ПДД. "
    "Вы можете прикрепить к вопросу документ (в формате PDF/DOCX/TXT)."
)

# ==============================================================================
# VIEW 1: ЧАТ
# ==============================================================================
if selected_view == "💬 RAG Ассистент (Чат)":
    if not user_profile or not active_chat:
        render_auth_gate()
        st.stop()

    # Заголовок БЕЗ court-иконки
    chat_title = active_chat.get("title", "Чат RAG-ассистента")
    if "Общие вопросы по раскату" in chat_title:
        chat_title = "Чат RAG-ассистента"
    st.markdown(f"<h2 style='margin:0 0 0.5rem 0;'>{chat_title}</h2>", unsafe_allow_html=True)

    messages = active_chat_messages
    messages = [m for m in messages if "Общие вопросы по раскату" not in m.get("content", "")]

    if not messages:
        with st.chat_message("assistant"):
            st.markdown(NEW_GREETING)

    for msg_idx, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            if msg.get("topics"):
                st.caption(f"Выделенные темы вопроса (Gemini): {' • '.join([f'`{t}`' for t in msg['topics']])}")

            if msg.get("attached_filename"):
                b2_key = msg.get("attached_b2_key")
                info_line = f"Прикрепленный документ: `{msg['attached_filename']}` ({msg.get('attached_chars', 0)} знаков)"
                if b2_key and B2StorageManager.is_configured():
                    presigned = B2StorageManager.get_presigned_url(b2_key)
                    if presigned:
                        info_line += f" • [Скачать из Backblaze B2]({presigned})"
                st.info(info_line)

            if msg.get("fallback_used"):
                with st.expander("Статус подключения Gemini (активирован сценарий из 5 базовых фрагментов)"):
                    st.warning(f"Причина переключения на локальный синтез: **{msg.get('fallback_reason')}**")
                    st.caption("Подробный лог сохранен в: `logs/gemini_connection.log`")

            rendered_md = inject_user_into_internal_links(msg["content"], current_user_email)
            st.markdown(rendered_md)

            sources = msg.get("sources") or []
            if sources:
                if len(sources) <= 5 or msg.get("fallback_used"):
                    exp_title = f"Использованные первоисточники ({len(sources)} базовых фрагментов)"
                else:
                    exp_title = f"Использованные первоисточники ({len(sources)} документов): 5 базовых + {len(sources) - 5} тематических"

                with st.expander(exp_title):
                    for s_idx, s in enumerate(sources):
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            tag_badge = "[Тематическое расширение]" if s.get("source_tag") == "topic_expansion" else "[Базовый поиск]"
                            src_url = inject_user_into_internal_links(s.get("url", "#"), current_user_email)
                            st.markdown(f"**[{s['title']}]({src_url})** `{tag_badge}`")
                            if s.get("case_number"):
                                st.caption(f"Дело №: {s['case_number']} | Дата: {s.get('date', 'Не указана')}")
                            st.text(f"Фрагмент: {s['matched_chunk'][:240]}...")

                            coll = s.get("collection", "")
                            doc_t = s.get("doc_type", "")
                            p_id = s.get("parent_id")
                            if (coll == "legal_laws" or doc_t == "legal_law") and p_id:
                                if st.button("Открыть статью в просмотрщике", key=f"hist_legal_{msg_idx}_{p_id}_{s_idx}"):
                                    st.session_state.current_nav = "📜 Нормативная база (ГК/НК РФ)"
                                    st.session_state.active_legal_doc_id = p_id
                                    _set_query_param_if_changed("doc", p_id)
                                    st.rerun()
                            elif (coll == "traffic_rules" or doc_t == "traffic_rules") and p_id:
                                if st.button("Открыть главу ПДД в просмотрщике", key=f"hist_pdd_{msg_idx}_{p_id}_{s_idx}"):
                                    st.session_state.current_nav = "🚦 Правила дорожного движения (ПДД РФ)"
                                    st.session_state.active_pdd_doc_id = p_id
                                    _set_query_param_if_changed("pdd", p_id)
                                    st.rerun()

                        with col_b:
                            st.metric("Rerank Score", f"{s.get('similarity_score', 0.0):.3f}")
                        st.divider()

    # Неблокирующий polling через @st.fragment(run_every=2) — без time.sleep и перезапуска всего скрипта
    @st.fragment(run_every=2)
    def _poll_active_job_fragment():
        job_id = st.session_state.get("active_job_id")
        if not job_id or job_id not in GLOBAL_JOBS:
            return
        job_info = GLOBAL_JOBS[job_id]
        status = job_info.get("status")

        if status in ("started", "retrieving", "generating"):
            with st.chat_message("assistant"):
                st.info("Формирование ответа в фоновом режиме... Вы можете переходить в «Нормативную базу» и «ПДД» — конвейер не прервется.")
                with st.spinner("Идет поиск первоисточников и генерация ответа..."):
                    pass

        elif status == "completed":
            if not job_info.get("finalized"):
                job_info["finalized"] = True
                res = job_info.get("result", {})
                new_msg = {
                    "role": "assistant",
                    "content": res.get("answer", ""),
                    "sources": res.get("sources", []),
                    "topics": res.get("topics", []),
                    "targets": res.get("targets", []),
                    "fallback_used": res.get("fallback_used", False),
                    "fallback_reason": res.get("fallback_reason"),
                }
                target_chat_id = job_info.get("chat_id") or active_chat["chat_id"]
                if not job_info.get("saved_in_db"):
                    ChatManager.append_message(user_profile, target_chat_id, new_msg)

                target_chat = next(
                    (c for c in user_profile.get("chats", []) if c.get("chat_id") == target_chat_id),
                    active_chat,
                )
                if "Новый диалог" in target_chat.get("title", "") and res.get("topics"):
                    ChatManager.rename_chat(user_profile, target_chat_id, res["topics"][0].capitalize())

                _invalidate_chat_caches()
            st.session_state.active_job_id = None
            try:
                st.rerun(scope="app")
            except TypeError:
                st.rerun()

        elif status == "error":
            st.error(f"Ошибка фонового конвейера: {job_info.get('error')}")
            st.session_state.active_job_id = None

    if st.session_state.get("active_job_id") in GLOBAL_JOBS:
        _poll_active_job_fragment()

    # --- Нижняя панель ввода (sticky CSS вместо приватного st._bottom): скрепка слева + поле ввода справа ---
    st.session_state.setdefault("file_uploader_nonce", 0)
    pending_file = st.session_state.get("pending_attachment")
    if pending_file:
        p_col1, p_col2 = st.columns([10, 2], vertical_alignment="center")
        p_col1.caption(f"Прикрепленный файл готов к отправке: **{pending_file['name']}** ({pending_file['size_kb']:.1f} КБ)")
        if p_col2.button("Убрать", key="btn_clear_pending_file", use_container_width=True):
            st.session_state.pending_attachment = None
            st.session_state._last_attached_sig = None
            st.session_state.file_uploader_nonce += 1
            st.rerun()

    col_attach, col_input = st.columns([1, 14], vertical_alignment="center")
    with col_attach:
        uploaded_file = st.file_uploader(
            "attach",
            type=["pdf", "docx", "txt", "md"],
            key=f"chat_file_attachment_{st.session_state.file_uploader_nonce}",
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            file_sig = f"{uploaded_file.name}:{uploaded_file.size}"
            if st.session_state.get("_last_attached_sig") != file_sig:
                f_bytes = uploaded_file.getvalue()
                st.session_state._last_attached_sig = file_sig
                st.session_state.pending_attachment = {
                    "name": uploaded_file.name,
                    "bytes": f_bytes,
                    "size_kb": len(f_bytes) / 1024.0,
                }
                st.rerun()
    with col_input:
        prompt = st.chat_input(
            "Задайте правовой вопрос по аренде с выкупом, налогам или ПДД...",
            key="main_chat_input",
        )

    if prompt:
        trigger_render_wakeup()

        file_text = ""
        file_name = None
        b2_key = None

        attachment_obj = st.session_state.get("pending_attachment")
        if attachment_obj:
            file_name = attachment_obj["name"]
            f_bytes = attachment_obj["bytes"]
            file_text = extract_text_from_file(f_bytes, file_name)

            if B2StorageManager.is_configured():
                b2_key = B2StorageManager.upload_user_attachment(
                    current_user_email, active_chat["chat_id"], file_name, f_bytes,
                )
                if b2_key and ChatManager.is_cloud_db_active():
                    SupabaseChatDB.record_document(
                        b2_key, current_user_email, active_chat["chat_id"], file_name, len(f_bytes),
                    )
            st.session_state.pending_attachment = None
            st.session_state._last_attached_sig = None
            st.session_state.file_uploader_nonce += 1

        user_entry = {
            "role": "user",
            "content": prompt,
            "attached_filename": file_name,
            "attached_chars": len(file_text) if file_text else 0,
            "attached_b2_key": b2_key,
        }
        ChatManager.append_message(user_profile, active_chat["chat_id"], user_entry)
        _invalidate_chat_caches()

        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        GLOBAL_JOBS[job_id] = {
            "status": "started",
            "user_id": current_user_email,
            "chat_id": active_chat.get("chat_id"),
            "result": None,
            "error": None,
            "saved_in_db": False,
        }
        st.session_state.active_job_id = job_id

        assistant_inst = get_rag_assistant()
        t = threading.Thread(
            target=_run_background_rag_task,
            args=(job_id, prompt, file_text, current_user_email, active_chat.get("chat_id"), assistant_inst),
            daemon=True,
        )
        t.start()
        st.rerun()


# ==============================================================================
# VIEW 2: НОРМАТИВНАЯ БАЗА
# ==============================================================================
elif selected_view == "📜 Нормативная база (ГК/НК РФ)":
    st.markdown(
        "<h2 style='margin:0 0 0.5rem 0;'>Нормативно-правовая база (ГК РФ / НК РФ / КоАП РФ / Лизинг)</h2>",
        unsafe_allow_html=True,
    )

    legal_items = load_legal_chapters()

    if not legal_items:
        st.info("Нормативные акты не найдены. Проверьте `data/legal/legal_chapters.jsonl` или синхронизацию Backblaze B2.")
    else:
        col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
        all_codes = sorted(list(set(d.get("code", d.get("section", "ГК РФ")) for d in legal_items if d.get("code") or d.get("section"))))
        with col_f1:
            # Только выпадающий список (без свободного ввода)
            selected_code = st.selectbox("Кодекс / Закон:", ["Все акты"] + all_codes)
        with col_f2:
            all_cats = sorted(list(set(d.get("category", "") for d in legal_items if d.get("category"))))
            # Только выпадающий список (без свободного ввода)
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

        active_id = st.session_state.get("active_legal_doc_id")
        active_doc = None
        if active_id:
            active_doc = next((d for d in legal_items if d.get("parent_id") == active_id or d.get("doc_id") == active_id), None)

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
                    st.subheader(f"{active_doc.get('title')}")
                    st.caption(f"{active_doc.get('code', 'ГК РФ')} | {active_doc.get('chapter_number', '')} | Тема: **{active_doc.get('category', 'Законодательство')}**")
                with col_h2:
                    p_lvl = active_doc.get("priority_level", "standard").upper()
                    st.caption(f"Приоритет: `{p_lvl}`")
                    st.markdown(f"[Первоисточник (docs.cntd.ru)]({active_doc.get('original_url', 'https://docs.cntd.ru')})")

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
                    st.subheader(f"{single_doc.get('title')}")
                    st.caption(f"{single_doc.get('code', 'ГК РФ')} | {single_doc.get('chapter_number', '')} | Тема: **{single_doc.get('category', 'Законодательство')}**")
                with col_h2:
                    p_lvl = single_doc.get("priority_level", "standard").upper()
                    st.caption(f"Приоритет: `{p_lvl}`")
                    st.markdown(f"[Первоисточник (docs.cntd.ru)]({single_doc.get('original_url', 'https://docs.cntd.ru')})")

                st.divider()
                st.markdown(single_doc.get("body", single_doc.get("full_text", "")))
                if single_doc.get("details"):
                    st.caption(f"Реквизиты: {single_doc.get('details')}")

        elif len(filtered_docs) > 1:
            st.info(f"**Список всех статей выборки:** Найдено **{len(filtered_docs)}** статей. Выберите статью для чтения:")
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
                        if st.button("Читать", key=f"open_art_{p_id}_{idx}", use_container_width=True):
                            st.session_state.active_legal_doc_id = p_id
                            _set_query_param_if_changed("doc", p_id)
                            st.rerun()
        else:
            st.warning("По заданным фильтрам статей не найдено. Попробуйте изменить параметры поиска.")


# ==============================================================================
# VIEW 3: ПДД
# ==============================================================================
elif selected_view == "🚦 Правила дорожного движения (ПДД РФ)":
    st.markdown(
        "<h2 style='margin:0 0 0.5rem 0;'>Правила дорожного движения</h2>",
        unsafe_allow_html=True,
    )

    pdd_items = load_pdd_chapters()

    if not pdd_items:
        st.warning("Файл ПДД не найден в `data/pdd/pdd_chapters.jsonl`.")
    else:
        active_pdd_id = st.session_state.get("active_pdd_doc_id")
        active_ch = next((c for c in pdd_items if c.get("parent_id") == active_pdd_id or c.get("doc_id") == active_pdd_id), None)

        def _fmt_pdd_option(c: Dict[str, Any]) -> str:
            num = str(c.get("chapter_number", "")).strip()
            title = str(c.get("chapter_title", c.get("title", ""))).strip()
            title = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", title)
            return f"{num} {title}".strip()

        ch_options = [_fmt_pdd_option(c) for c in pdd_items]
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
            st.subheader(f"{cur_ch.get('title')}")
            st.caption(f"{cur_ch.get('chapter_number', '')} | ID: `{cur_ch.get('parent_id')}`")
            st.divider()

            ch_body = cur_ch.get("body", cur_ch.get("full_text", ""))
            if search_kw.strip():
                kw = search_kw.lower()
                highlighted_lines = []
                for line in ch_body.split("\n"):
                    if kw in line.lower():
                        highlighted_lines.append(f"**{line.strip()}**")
                    else:
                        highlighted_lines.append(line)
                st.markdown("\n".join(highlighted_lines))
            else:
                st.markdown(ch_body)

        with st.expander(f"Полное оглавление Правил дорожного движения ({len(pdd_items)} разделов)"):
            for ch in pdd_items:
                ch_pid = ch.get("parent_id", "")
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{_fmt_pdd_option(ch)}**")
                if c2.button("Перейти", key=f"nav_pdd_ch_{ch_pid}"):
                    st.session_state.active_pdd_doc_id = ch_pid
                    _set_query_param_if_changed("pdd", ch_pid)
                    st.rerun()