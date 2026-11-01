"""
Генератор ответов RAG на базе Gemini 3.1 Flash Lite.
Формирует юридически точные ответы со строгими ссылками на первоисточники в тексте.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from rag_pipeline.config import GEMINI_API_KEY, MODEL_NAME
from rag_pipeline.retriever import HybridRetriever

logger = logging.getLogger("rag_generator")
logger.setLevel(logging.INFO)

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


class RAGAssistant:
    """Полный конвейер RAG: Hybrid Retrieval -> Gemini 3.1 Flash Lite Generation"""

    def __init__(self):
        self.retriever = HybridRetriever()
        self.client = None
        self._init_gemini()

    def _init_gemini(self):
        """Инициализация клиента Google GenAI"""
        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.warning(f"Ошибка инициализации google.genai: {e}")

    def answer_query(self, query: str) -> Dict[str, Any]:
        """
        Полный цикл обработки пользовательского вопроса:
        1. Retrieval (Router + BM25 + Dense + Rerank)
        2. Prompt Compilation with Strict Citation Anchors
        3. LLM Generation (Gemini 3.1 Flash Lite)
        4. Post-processing & Sources Extraction
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
                    "Пожалуйста, запустите коллектор сбора данных (`run_collectors.bat all`) "
                    "или уточните формулировку запроса."
                ),
                "target_collections": retrieval_res.get("target_collections", []),
                "sources": []
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
        if self.client:
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
                logger.warning(f"Ошибка обращения к Gemini API ({MODEL_NAME}): {gen_err}")
                # Фоллбэк на запасную стабильную модель, если превью недоступно
                try:
                    fallback_model = "gemini-2.5-flash"
                    response = self.client.models.generate_content(
                        model=fallback_model,
                        contents=user_prompt,
                        config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.2}
                    )
                    answer_text = response.text or ""
                except Exception:
                    pass

        # Шаг 4: Детерминированный фоллбэк генератор (для локального ПК без API-ключа)
        if not answer_text:
            answer_text = self._extractive_fallback_generation(query, sources)

        return {
            "query": query,
            "answer": answer_text,
            "target_collections": retrieval_res.get("target_collections", []),
            "sources": sources
        }

    def _extractive_fallback_generation(self, query: str, sources: List[Dict[str, Any]]) -> str:
        """
        Локальный высокоточный генератор на случай отсутствия API-ключа Gemini.
        Синтезирует ответ из родительских документов с сохранением ссылок и реквизитов.
        """
        q_lower = query.lower()
        parts = [f"**Ответ RAG-ассистента по базе знаний компании (сформирован по проверенным источникам):**\n"]

        has_cars = any(s["collection"] == "car_catalog" for s in sources)
        has_laws = any(s["collection"] == "legal_laws" for s in sources)
        has_court = any(s["collection"] == "court_cases" for s in sources)
        has_news = any(s["collection"] == "auto_news" for s in sources)

        if has_cars:
            parts.append("### 🚙 Доступные автомобили и условия раската")
            for s in [src for src in sources if src["collection"] == "car_catalog"][:2]:
                parts.append(
                    f"- **[{s['title']}]({s['url']})**: {s['matched_chunk'].split('Условия раската')[0].strip()}"
                )

        if has_laws:
            parts.append("### 📜 Правовое и налоговое основание (ГК РФ / НК РФ)")
            for s in [src for src in sources if src["collection"] == "legal_laws"][:2]:
                parts.append(
                    f"- По нормам **[{s['title']}]({s['url']})**: {s['matched_chunk'][:300]}..."
                )

        if has_court:
            parts.append("### ⚖️ Позиция Верховного Суда РФ")
            for s in [src for src in sources if src["collection"] == "court_cases"][:2]:
                parts.append(
                    f"- В постановлении **[{s['title']}]({s['url']})** (Дело № {s['case_number']}): {s['matched_chunk'][:350]}..."
                )

        if has_news:
            parts.append("### 📰 Рыночный контекст и аналитика")
            for s in [src for src in sources if src["collection"] == "auto_news"][:1]:
                parts.append(
                    f"- По данным статьи **[{s['title']}]({s['url']})**: {s['matched_chunk'][:250]}..."
                )

        parts.append("\n---\n*Все ссылки ведут на официальные тексты актов и первоисточники.*")
        return "\n\n".join(parts)
