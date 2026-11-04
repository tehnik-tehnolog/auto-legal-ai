"""
Генератор ответов RAG на базе Gemini 3.1 Flash Lite.
Формирует юридически точные ответы со строгими ссылками на первоисточники в тексте.
Ведет подробный аудит ошибок подключения к Gemini в logs/gemini_connection.log.
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_pipeline.config import GEMINI_API_KEY, LOGS_DIR, MODEL_NAME
from rag_pipeline.retriever import HybridRetriever

# Настройка специализированного логгера для Gemini и конвейера
logger = logging.getLogger("rag_generator")
logger.setLevel(logging.INFO)

GEMINI_LOG_FILE = LOGS_DIR / "gemini_connection.log"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Отдельный FileHandler для фиксации всех событий и ошибок подключения
_fh = logging.FileHandler(GEMINI_LOG_FILE, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
logger.addHandler(_fh)


SYSTEM_PROMPT = """Вы — ведущий юридический и коммерческий ИИ-консультант компании по раскату (аренде автомобилей с последующим выкупом) в Российской Федерации.

Ваша задача: давать точные, практические и юридически безупречные ответы на основе предоставленного контекста (статьи ГК РФ и НК РФ, судебная практика Верховного Суда РФ, каталог авто raskatof.ru и автоновости).

ПРАВИЛА ЦИТИРОВАНИЯ И ГЕНЕРАЦИИ (СТРОГО ОБЯЗАТЕЛЬНЫ):
1. КАЖДОЕ утверждение, правовая норма, ставка или судебная позиция ОБЯЗАНЫ сопровождаться ссылкой на первоисточник из контекста:
   - Для законов: [Название статьи ГК/НК РФ](URL_ИЗ_КОНТЕКСТА)
   - Для судебных дел: [Определение ВС РФ № ДЕЛА от ДАТЫ](URL_ИЗ_КОНТЕКСТА)
   - Для автомобилей: [Модель авто](URL_ИЗ_КОНТЕКСТА)
2. Не придумывайте ссылки и реквизиты — используйте ТОЛЬКО те URL и реквизиты, которые явно даны в блоках [Источник #N].
3. Если информации в предоставленном контексте недостаточно для полного ответа, прямо укажите, каких сведений не хватает, не додумывая законы.
4. Структурируйте ответ: краткий прямой вывод, правовое или фактическое обоснование, ссылки на нормы и судебную практику, практические рекомендации для договора раската.
"""


def _log_gemini_error(event_type: str, query: str, reason: str, details: str = "", tb: str = ""):
    """Запись подробного отчета об ошибке в logs/gemini_connection.log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n{'=' * 80}\n"
        f"[{timestamp}] [EVENT: {event_type}]\n"
        f"Вопрос пользователя: {query}\n"
        f"Причина вызова fallback: {reason}\n"
        f"Модель: {MODEL_NAME}\n"
    )
    if details:
        entry += f"Детали: {details}\n"
    if tb:
        entry += f"Стек вызовов (Traceback):\n{tb}\n"
    entry += f"{'=' * 80}\n"

    try:
        with open(GEMINI_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as io_err:
        print(f"[ERROR writing to {GEMINI_LOG_FILE}]: {io_err}", file=sys.stderr)


class RAGAssistant:
    """Полный конвейер RAG: Hybrid Retrieval -> Gemini 3.1 Flash Lite Generation"""

    def __init__(self):
        self.retriever = HybridRetriever()
        self.client = None
        self.init_error: Optional[str] = None
        self._init_gemini()

    def _init_gemini(self):
        """Инициализация клиента Google GenAI с детальной диагностикой"""
        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            self.init_error = "GEMINI_API_KEY не задан в переменных окружения или файле .env"
            logger.info(f"Диагностика Gemini: {self.init_error}")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.init_error = None
            logger.info(f"Клиент Google GenAI успешно инициализирован (модель: {MODEL_NAME})")
        except ImportError as imp_err:
            self.init_error = f"Библиотека google-genai не установлена: {imp_err}. Выполните: pip install google-genai"
            logger.warning(self.init_error)
            _log_gemini_error("IMPORT_ERROR", "system_init", self.init_error, str(imp_err), traceback.format_exc())
        except Exception as init_err:
            self.init_error = f"Ошибка инициализации genai.Client: {init_err}"
            logger.error(self.init_error)
            _log_gemini_error("CLIENT_INIT_ERROR", "system_init", self.init_error, str(init_err), traceback.format_exc())

    def answer_query(self, query: str) -> Dict[str, Any]:
        """
        Полный цикл обработки пользовательского вопроса:
        1. Retrieval (Router + BM25 + Dense + Rerank)
        2. Prompt Compilation with Strict Citation Anchors
        3. LLM Generation (Gemini 3.1 Flash Lite)
        4. Post-processing & Sources Extraction
        5. Detailed error logging to logs/gemini_connection.log if fallback triggers
        """
        # Шаг 1: Извлечение релевантных контекстов
        retrieval_res = self.retriever.retrieve(query)
        sources = retrieval_res["sources"]
        context_text = retrieval_res["formatted_context"]

        if not sources or not context_text.strip():
            return {
                "query": query,
                "answer": (
                    "В базе знаний компании не найдено релевантных документов по вашему вопросу. "
                    "Пожалуйста, запустите переиндексацию (`reindex_rag.bat`) "
                    "или коллектор сбора данных (`run_collectors.bat all`)."
                ),
                "target_collections": retrieval_res.get("target_collections", []),
                "sources": [],
                "fallback_used": False,
                "fallback_reason": None,
                "gemini_status": "no_context"
            }

        # Шаг 2: Формирование промпта
        user_prompt = f"""КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ КОМПАНИИ:
{context_text}

---
ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{query}

Дайте структурированный, исчерпывающий ответ на русском языке со ссылками на первоисточники в формате Markdown."""

        # Шаг 3: Генерация через Gemini
        answer_text = ""
        fallback_reason: Optional[str] = None
        gemini_status = "ok"

        if not self.client:
            fallback_reason = self.init_error or "Клиент Gemini не инициализирован (отсутствует GEMINI_API_KEY)"
            gemini_status = "missing_key" if "GEMINI_API_KEY" in fallback_reason else "init_failed"
        else:
            try:
                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=user_prompt,
                    config={
                        "system_instruction": SYSTEM_PROMPT,
                        "temperature": 0.2,  # Низкая температура для юридической строгости
                    }
                )
                answer_text = response.text or ""
            except Exception as gen_err:
                err_type = type(gen_err).__name__
                err_msg = str(gen_err)
                tb_str = traceback.format_exc()
                logger.warning(f"Ошибка вызова Gemini API ({MODEL_NAME}): {err_type} - {err_msg}")

                # Попытка обращения к резервной модели
                fallback_model = "gemini-2.5-flash"
                try:
                    logger.info(f"Попытка обращения к резервной модели {fallback_model}...")
                    response = self.client.models.generate_content(
                        model=fallback_model,
                        contents=user_prompt,
                        config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.2}
                    )
                    answer_text = response.text or ""
                    if answer_text:
                        logger.info(f"Ответ успешно получен от резервной модели {fallback_model}")
                except Exception as fb_err:
                    fallback_reason = (
                        f"Основная модель ({MODEL_NAME}) вернула ошибку: [{err_type}] {err_msg}. "
                        f"Резервная модель ({fallback_model}) также завершилась ошибкой: {fb_err}"
                    )
                    gemini_status = "api_error"
                    _log_gemini_error(
                        "API_CALL_FAILED",
                        query,
                        fallback_reason,
                        details=f"Prompt Length: {len(user_prompt)} chars",
                        tb=tb_str
                    )

        # Шаг 4: Детерминированный фоллбэк генератор (для локального ПК без API-ключа)
        fallback_used = False
        if not answer_text:
            fallback_used = True
            if not fallback_reason:
                fallback_reason = "Ответ от Gemini пуст или заблокирован фильтрами безопасности"

            # Логируем активацию фоллбэка
            _log_gemini_error(
                "FALLBACK_ACTIVATED",
                query,
                fallback_reason,
                details=f"Загружен детерминированный синтез _extractive_fallback_generation для {len(sources)} источников"
            )

            # Вывод предупреждения в консоль PyCharm
            print(
                f"\n⚠️  [RAG ASSISTANT WARNING] Загружен _extractive_fallback_generation!\n"
                f"    Причина: {fallback_reason}\n"
                f"    Подробный лог сохранен в: {GEMINI_LOG_FILE}\n",
                file=sys.stderr
            )

            answer_text = self._extractive_fallback_generation(query, sources, reason=fallback_reason)

        return {
            "query": query,
            "answer": answer_text,
            "target_collections": retrieval_res.get("target_collections", []),
            "sources": sources,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "gemini_status": gemini_status,
            "log_file": str(GEMINI_LOG_FILE)
        }

    def _extractive_fallback_generation(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        reason: Optional[str] = None
    ) -> str:
        """
        Локальный высокоточный генератор на случай отсутствия API-ключа Gemini или сетевых сбоев.
        Синтезирует ответ из родительских документов с сохранением ссылок и реквизитов.
        """
        parts = [
            "**Ответ RAG-ассистента по базе знаний компании (сформирован локально по первоисточникам):**\n"
        ]

        if reason and "GEMINI_API_KEY" in reason:
            parts.append(
                "> 💡 *Примечание: Для подключения генеративной нейросети Gemini 3.1 Flash Lite укажите "
                "`GEMINI_API_KEY` в файле `.env` или настройках PyCharm. Логи: `logs/gemini_connection.log`.*\n"
            )

        has_cars = any(s["collection"] == "car_catalog" for s in sources)
        has_laws = any(s["collection"] == "legal_laws" for s in sources)
        has_court = any(s["collection"] == "court_cases" for s in sources)
        has_news = any(s["collection"] == "auto_news" for s in sources)

        if has_cars:
            parts.append("### 🚙 Доступные автомобили и условия раската (raskatof.ru)")
            for s in [src for src in sources if src["collection"] == "car_catalog"][:2]:
                parts.append(
                    f"- **[{s['title']}]({s['url']})**: {s['matched_chunk'].split('Условия раската')[0].strip()}"
                )

        if has_laws:
            parts.append("### 📜 Правовое и налоговое основание (ГК РФ / НК РФ)")
            for s in [src for src in sources if src["collection"] == "legal_laws"][:3]:
                meta = s.get("metadata", {})
                sec = meta.get("section", "Законодательство")
                cat = meta.get("category", "")
                cat_label = f" ({cat})" if cat else ""
                parts.append(
                    f"- По нормам **[{s['title']}]({s['url']})**{cat_label}: {s['matched_chunk'][:300]}..."
                )

        if has_court:
            parts.append("### ⚖️ Позиция Верховного Суда РФ")
            for s in [src for src in sources if src["collection"] == "court_cases"][:2]:
                case_no = s.get("case_number", "не указан")
                parts.append(
                    f"- В постановлении **[{s['title']}]({s['url']})** (Дело № {case_no}): {s['matched_chunk'][:350]}..."
                )

        if has_news:
            parts.append("### 📰 Рыночный контекст и аналитика")
            for s in [src for src in sources if src["collection"] == "auto_news"][:1]:
                parts.append(
                    f"- По данным статьи **[{s['title']}]({s['url']})**: {s['matched_chunk'][:250]}..."
                )

        parts.append("\n---\n*Все ссылки ведут на официальные тексты актов и первоисточники.*")
        return "\n\n".join(parts)
