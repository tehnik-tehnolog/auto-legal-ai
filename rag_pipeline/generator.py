"""
RAG Answer Generator powered by Gemini 3.1 Flash Lite and a two-stage retrieval pipeline:
1. Invoke Gemini to extract 2-6 search topics from the legal query.
2. Collect ~40 candidate articles across those topics + rerank (select top 5 articles).
3. Merge with 5 standard retrieval chunks = TOTAL 10 primary sources.
4. Call Gemini (or deterministic fallback) with detailed diagnostics logging.
"""

import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_pipeline.config import (
    COLLECTION_COURT,
    COLLECTION_LAWS,
    COLLECTION_NEWS,
    COLLECTION_PDD,
    GEMINI_API_KEY,
    LOGS_DIR,
    MODEL_NAME,
)
from rag_pipeline.retriever import HybridRetriever
from rag_pipeline.promts import (SYSTEM_PROMPT, TOPIC_PROMPT)

# Configure dedicated file logger for Gemini and the RAG pipeline
logger = logging.getLogger("rag_generator")
logger.setLevel(logging.INFO)

GEMINI_LOG_FILE = LOGS_DIR / "gemini_connection.log"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

_fh = logging.FileHandler(GEMINI_LOG_FILE, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
logger.addHandler(_fh)

def _log_gemini_error(event_type: str, query: str, reason: str, details: str = "", tb: str = ""):
    """Write a detailed error report to logs/gemini_connection.log."""
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
    """End-to-end RAG pipeline with two-stage topic expansion (10 sources) and answer generation."""

    def __init__(self):
        self.retriever = HybridRetriever()
        self.client = None
        self.init_error: Optional[str] = None
        self._init_gemini()

    def _init_gemini(self):
        """Initialize the Google GenAI client with detailed diagnostics."""
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

    def extract_topics(self, query: str, client: Optional[Any] = None) -> tuple[List[str], bool]:
        """
        Stage 1 of the two-stage pipeline: ask Gemini to extract 2-6 key topics/subqueries.
        Returns (topics, gemini_connected).
        If connecting to the Gemini API fails, returns ([], False) so retrieval is capped at 5 standard chunks.
        """
        active_client = client or self.client
        if not active_client:
            return [], False

        try:
            topic_prompt = TOPIC_PROMPT(query)
            res = active_client.models.generate_content(
                model=MODEL_NAME,
                contents=topic_prompt,
                config={"temperature": 0.1}
            )
            text = (res.text or "").strip()
            json_match = re.search(r'\[\s*".*?"\s*\]', text, re.DOTALL)
            if json_match:
                topics = json.loads(json_match.group(0))
                cleaned = [str(t).strip() for t in topics[:6] if str(t).strip()] if isinstance(topics, list) else []
                if len(cleaned) >= 2:
                    return cleaned, True
            # Gemini connected successfully, even if fewer than 2 topics were returned
            return [], True
        except Exception as e:
            logger.warning(f"Не удалось подключиться к Gemini API на этапе выделения тем ({e}). Используем только 5 базовых фрагментов.")
            _log_gemini_error("TOPIC_EXTRACTION_FAILED", query, f"Ошибка подключения к Gemini: {e}")
            return [], False

    def prepare_10_sources_context(
        self,
        query: str,
        attached_doc_text: str = "",
        client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Two-stage context assembly:
        - When Gemini API is available: 5 standard fragments + 5 top articles from topic expansion (~40 candidates) = 10 total.
        - When Gemini API connection fails: ONLY 5 standard fragments.
        """
        # Step 1: Standard retrieval (5 fragments)
        standard_res = self.retriever.retrieve(query, top_k=5)
        standard_sources = standard_res.get("sources", [])[:5]
        standard_parent_ids = {s.get("parent_id") for s in standard_sources if s.get("parent_id")}
        standard_chunk_ids = {s.get("chunk_id") for s in standard_sources if s.get("chunk_id")}

        # Tag standard sources and set internal viewer URLs for the web UI
        for s in standard_sources:
            s["source_tag"] = "standard_retrieval"
            if s.get("parent_id") and s.get("collection") == COLLECTION_LAWS:
                s["url"] = f"?doc={s['parent_id']}#doc-legal_{s['parent_id']}"
            elif s.get("parent_id") and s.get("collection") == COLLECTION_PDD:
                s["url"] = f"?pdd={s['parent_id']}#doc-pdd_{s['parent_id']}"

        # Step 2: Extract 2-6 search topics via Gemini
        topics, gemini_connected = self.extract_topics(query, client=client or self.client)
        logger.info(f"Gemini connected={gemini_connected} | Темы по вопросу: {topics}")

        topic_sources: List[Dict[str, Any]] = []

        # If Gemini API succeeded and topics were extracted, expand pool to 10 sources
        if gemini_connected and topics:
            topic_candidates_map: Dict[str, Dict[str, Any]] = {}
            target_colls = [COLLECTION_LAWS, COLLECTION_COURT, COLLECTION_PDD]

            for topic in topics:
                for coll in target_colls:
                    if coll in self.retriever.bm25_indices:
                        hits = self.retriever.bm25_indices[coll].search(topic, top_k=6)
                        for rank, (doc_id, bm_score) in enumerate(hits):
                            if doc_id in self.retriever.bm25_indices[coll].docs_map:
                                chunk_obj = self.retriever.bm25_indices[coll].docs_map[doc_id]
                                if doc_id not in topic_candidates_map:
                                    topic_candidates_map[doc_id] = {
                                        "id": doc_id,
                                        "collection": coll,
                                        "text": chunk_obj["text"],
                                        "metadata": chunk_obj.get("metadata", {}),
                                        "rrf_score": 1.0 / (60.0 + rank)
                                    }

                    dense_hits = self.retriever._dense_search(coll, topic, top_k=6)
                    for rank, (doc_id, sim, meta, text) in enumerate(dense_hits):
                        if doc_id not in topic_candidates_map:
                            topic_candidates_map[doc_id] = {
                                "id": doc_id,
                                "collection": coll,
                                "text": text,
                                "metadata": meta,
                                "rrf_score": 1.0 / (60.0 + rank)
                            }

            all_topic_candidates = list(topic_candidates_map.values())
            ranked_topic_candidates = self.retriever._rerank_candidates(query, all_topic_candidates)

            seen_parents = set(standard_parent_ids)
            seen_chunks = set(standard_chunk_ids)

            for item in ranked_topic_candidates:
                if len(topic_sources) >= 5:
                    break
                meta = item.get("metadata", {})
                p_id = meta.get("parent_id")
                c_id = item["id"]

                if p_id and p_id in seen_parents:
                    continue
                if c_id in seen_chunks:
                    continue

                parent_doc = self.retriever.parent_store.get(p_id, {})
                title = parent_doc.get("title") or meta.get("title", "Документ")
                clean_pid = p_id or c_id
                if item.get("collection") == COLLECTION_LAWS:
                    url = f"?doc={clean_pid}#doc-legal_{clean_pid}"
                elif item.get("collection") == COLLECTION_PDD:
                    url = f"?pdd={clean_pid}#doc-pdd_{clean_pid}"
                else:
                    url = parent_doc.get("url") or meta.get("url", "#")

                topic_sources.append({
                    "chunk_id": c_id,
                    "parent_id": p_id,
                    "collection": item["collection"],
                    "title": title,
                    "url": url,
                    "doc_type": meta.get("doc_type", "legal_law"),
                    "case_number": parent_doc.get("case_number") or meta.get("case_number", ""),
                    "date": parent_doc.get("date") or meta.get("date", ""),
                    "similarity_score": item.get("rerank_score", 0.0),
                    "matched_chunk": item["text"],
                    "source_tag": "topic_expansion"
                })
                if p_id:
                    seen_parents.add(p_id)
                seen_chunks.add(c_id)

            if len(topic_sources) < 5:
                for item in ranked_topic_candidates:
                    if len(topic_sources) >= 5:
                        break
                    c_id = item["id"]
                    if c_id not in seen_chunks:
                        meta = item.get("metadata", {})
                        p_id = meta.get("parent_id")
                        parent_doc = self.retriever.parent_store.get(p_id, {})
                        title = parent_doc.get("title") or meta.get("title", "Документ")
                        clean_pid = p_id or c_id
                        if item.get("collection") == COLLECTION_LAWS:
                            url = f"?doc={clean_pid}#doc-legal_{clean_pid}"
                        elif item.get("collection") == COLLECTION_PDD:
                            url = f"?pdd={clean_pid}#doc-pdd_{clean_pid}"
                        else:
                            url = parent_doc.get("url") or meta.get("url", "#")
                        topic_sources.append({
                            "chunk_id": c_id,
                            "parent_id": p_id,
                            "collection": item["collection"],
                            "title": title,
                            "url": url,
                            "doc_type": meta.get("doc_type", "legal_law"),
                            "case_number": parent_doc.get("case_number") or meta.get("case_number", ""),
                            "date": parent_doc.get("date") or meta.get("date", ""),
                            "similarity_score": item.get("rerank_score", 0.0),
                            "matched_chunk": item["text"],
                            "source_tag": "topic_expansion"
                        })
                        seen_chunks.add(c_id)

        # Merge sources: 10 when Gemini is reachable, otherwise ONLY 5 baseline fragments
        final_sources = standard_sources + topic_sources
        for idx, s in enumerate(final_sources, 1):
            s["citation_id"] = idx

        # Build context blocks for the LLM prompt
        context_blocks = []
        for s in final_sources:
            tag_label = "Базовый поиск" if s.get("source_tag") == "standard_retrieval" else "Тематическое расширение"
            block = (
                f"[Источник #{s['citation_id']}] ({s['collection']} | {tag_label})\n"
                f"Заголовок: {s['title']}\n"
                f"Ссылка: {s['url']}\n"
            )
            if s.get("case_number"):
                block += f"Номер дела: {s['case_number']} (Дата: {s.get('date', 'н/д')})\n"
            block += f"Текст нормы / фрагмента:\n{s['matched_chunk']}\n"
            context_blocks.append(block)

        formatted_context = "\n---\n".join(context_blocks)

        user_prompt = f"""КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ КОМПАНИИ ({len(final_sources)} ПРОВЕРЕННЫХ ПЕРВОИСТОЧНИКОВ):
{formatted_context}
"""
        if attached_doc_text.strip():
            user_prompt += f"""
---
[ПРИКРЕПЛЕННЫЙ ДОКУМЕНТ ЮРИСТА ДЛЯ АНАЛИЗА]:
{attached_doc_text.strip()[:6000]}
"""

        user_prompt += f"""
---
ВОПРОС ЮРИСТА:
{query}

Дай структурированный, исчерпывающий ответ на русском языке со ссылками на первоисточники в формате Markdown."""

        return {
            "query": query,
            "topics": topics,
            "gemini_connected": gemini_connected,
            "standard_count": len(standard_sources),
            "topic_count": len(topic_sources),
            "total_count": len(final_sources),
            "sources": final_sources,
            "formatted_context": formatted_context,
            "user_prompt": user_prompt,
            "target_collections": standard_res.get("target_collections", [])
        }

    def generate_with_gemini(
        self,
        user_prompt: str,
        client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Send the compiled prompt to Gemini 3.1 Flash Lite."""
        active_client = client or self.client
        if not active_client:
            reason = self.init_error or "Клиент Gemini не инициализирован (отсутствует GEMINI_API_KEY)"
            return {
                "answer": "",
                "status": "missing_key" if "GEMINI_API_KEY" in reason else "init_failed",
                "error": reason
            }

        try:
            response = active_client.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "temperature": 0.2,
                }
            )
            text = response.text or ""
            return {"answer": text, "status": "ok", "error": None}
        except Exception as gen_err:
            err_type = type(gen_err).__name__
            err_msg = str(gen_err)
            logger.warning(f"Ошибка вызова Gemini API ({MODEL_NAME}): {err_type} - {err_msg}")

            # Backup model
            fallback_model = "gemini-2.5-flash"
            try:
                logger.info(f"Попытка обращения к резервной модели {fallback_model}...")
                response = active_client.models.generate_content(
                    model=fallback_model,
                    contents=user_prompt,
                    config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.2}
                )
                text = response.text or ""
                if text:
                    return {"answer": text, "status": "ok_fallback_model", "error": None}
            except Exception as fb_err:
                full_reason = f"Основная модель ({MODEL_NAME}) вернула: [{err_type}] {err_msg}. Резервная модель: {fb_err}"
                _log_gemini_error("API_CALL_FAILED", user_prompt[:150], full_reason, tb=traceback.format_exc())
                return {"answer": "", "status": "api_error", "error": full_reason}

        return {"answer": "", "status": "empty_response", "error": "Пустой ответ"}

    def answer_query(self, query: str, attached_doc_text: str = "") -> Dict[str, Any]:
        """Full RAG cycle: 10 sources with Gemini or strictly 5 baseline fragments on API failure."""
        ctx_data = self.prepare_10_sources_context(query, attached_doc_text=attached_doc_text)
        sources = ctx_data["sources"]
        user_prompt = ctx_data["user_prompt"]
        topics = ctx_data["topics"]

        gemini_res = self.generate_with_gemini(user_prompt)
        answer_text = gemini_res["answer"]
        fallback_used = False
        fallback_reason = gemini_res.get("error")

        if not answer_text:
            fallback_used = True
            if not fallback_reason:
                fallback_reason = "Ответ от Gemini пуст или заблокирован фильтрами"
            _log_gemini_error("FALLBACK_ACTIVATED", query, fallback_reason)
            # Keep strictly 5 baseline fragments when Gemini API cannot be reached
            sources = [s for s in sources if s.get("source_tag") == "standard_retrieval"][:5] or sources[:5]
            topics = []
            answer_text = self._extractive_fallback_generation(query, sources, reason=fallback_reason)

        return {
            "query": query,
            "answer": answer_text,
            "topics": topics,
            "target_collections": ctx_data.get("target_collections", []),
            "sources": sources,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "gemini_status": gemini_res["status"],
            "log_file": str(GEMINI_LOG_FILE)
        }

    def _extractive_fallback_generation(
        self,
        query: str,
        sources:

        List[Dict[str, Any]],
        reason: Optional[str] = None
    ) -> str:
        """Extractive fallback generator when Gemini API key is missing or network fails."""
        parts = [
            "**Ответ RAG-ассистента по базе знаний компании (сформирован локально по первоисточникам):**\n"
        ]

        if reason and "GEMINI_API_KEY" in reason:
            parts.append(
                "> 💡 *Примечание: Для подключения генеративной нейросети Gemini 3.1 Flash Lite укажите "
                "`GEMINI_API_KEY` в файле `.env` или настройках IDE. Логи: `logs/gemini_connection.log`.*\n"
            )

        laws_sources = [s for s in sources if s["collection"] == COLLECTION_LAWS]
        court_sources = [s for s in sources if s["collection"] == COLLECTION_COURT]
        pdd_sources = [s for s in sources if s["collection"] == COLLECTION_PDD]
        news_sources = [s for s in sources if s["collection"] == COLLECTION_NEWS]

        if laws_sources:
            parts.append("### 📜 Нормативно-правовое основание (ГК / НК / КоАП РФ)")
            for s in laws_sources[:5]:
                parts.append(
                    f"- По нормам **[{s['title']}]({s['url']})**: {s['matched_chunk'][:300]}..."
                )

        if pdd_sources:
            parts.append("### 🚦 Правила дорожного движения РФ (ПДД РФ)")
            for s in pdd_sources[:3]:
                parts.append(
                    f"- По правилам **[{s['title']}]({s['url']})**: {s['matched_chunk'][:350]}..."
                )

        if court_sources:
            parts.append("### ⚖️ Позиция Верховного Суда РФ")
            for s in court_sources[:2]:
                case_no = s.get("case_number", "не указан")
                parts.append(
                    f"- В постановлении **[{s['title']}]({s['url']})** (Дело № {case_no}): {s['matched_chunk'][:350]}..."
                )

        if news_sources:
            parts.append("### 📰 Рыночный контекст и аналитика")
            for s in news_sources[:2]:
                parts.append(
                    f"- По данным статьи **[{s['title']}]({s['url']})**: {s['matched_chunk'][:250]}..."
                )

        parts.append("\n---\n*Ссылки ведут на локальные статьи и официальные первоисточники.*")
        return "\n\n".join(parts)
