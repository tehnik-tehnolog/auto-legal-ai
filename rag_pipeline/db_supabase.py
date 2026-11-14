"""
Клиент базы данных Supabase (PostgreSQL) для хранения профилей пользователей (Email + Имя),
тем чатов, закрепленных диалогов (pin), истории сообщений и метаданных документов из Backblaze B2.
Адаптирован под Render Free Tier (авто-создание таблиц при старте, устойчивость к пробуждению).
"""

import json
import logging
from typing import Any, Dict, List, Optional

from rag_pipeline.config import (
    DATABASE_URL,
    SUPABASE_DBNAME,
    SUPABASE_HOST,
    SUPABASE_PASSWORD,
    SUPABASE_PORT,
    SUPABASE_USER,
)

logger = logging.getLogger("db_supabase")


class SupabaseChatDB:
    """Репозиторий пользователей, чатов и сообщений на базе Supabase PostgreSQL"""

    _schema_initialized = False

    @classmethod
    def is_configured(cls) -> bool:
        if DATABASE_URL:
            return True
        return bool(SUPABASE_HOST and SUPABASE_USER and SUPABASE_PASSWORD)

    @classmethod
    def _connect(cls):
        import psycopg2

        if DATABASE_URL:
            return psycopg2.connect(DATABASE_URL, connect_timeout=10)

        return psycopg2.connect(
            host=SUPABASE_HOST,
            port=SUPABASE_PORT,
            user=SUPABASE_USER,
            password=SUPABASE_PASSWORD,
            dbname=SUPABASE_DBNAME or "postgres",
            sslmode="require",
            connect_timeout=10,
        )

    @classmethod
    def init_schema(cls) -> bool:
        """Создание таблиц в Supabase при первом обращении (так как на Render Free Tier нет shell)"""
        if not cls.is_configured():
            return False
        if cls._schema_initialized:
            return True

        ddl = """
        CREATE TABLE IF NOT EXISTS rag_users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            active_chat_id TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_login_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS rag_chats (
            chat_id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL REFERENCES rag_users(email) ON DELETE CASCADE,
            title TEXT NOT NULL,
            pinned BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_rag_chats_user_email ON rag_chats(user_email);

        CREATE TABLE IF NOT EXISTS rag_messages (
            id SERIAL PRIMARY KEY,
            chat_id TEXT NOT NULL REFERENCES rag_chats(chat_id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources JSONB DEFAULT '[]'::jsonb,
            topics JSONB DEFAULT '[]'::jsonb,
            targets JSONB DEFAULT '[]'::jsonb,
            attached_filename TEXT,
            attached_chars INTEGER DEFAULT 0,
            attached_b2_key TEXT,
            fallback_used BOOLEAN DEFAULT FALSE,
            fallback_reason TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_rag_messages_chat_id ON rag_messages(chat_id);

        CREATE TABLE IF NOT EXISTS rag_documents (
            doc_key TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            chat_id TEXT,
            filename TEXT NOT NULL,
            size_bytes BIGINT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(ddl)
            cls._schema_initialized = True
            logger.info("Схема таблиц Supabase PostgreSQL успешно проверена/создана.")
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации схемы Supabase: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def register_or_login_user(cls, email: str, name: str, initial_chat: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Регистрация нового пользователя (Имя + Email без подтверждения письма) или вход существующего."""
        if not cls.init_schema():
            return None

        norm_email = email.strip().lower()
        clean_name = name.strip() or norm_email.split("@")[0]

        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT email, name, active_chat_id FROM rag_users WHERE email = %s",
                        (norm_email,),
                    )
                    row = cur.fetchone()
                    if row:
                        # Обновляем время входа и имя, если передано новое непустое имя
                        cur.execute(
                            """
                            UPDATE rag_users
                            SET name = CASE WHEN %s <> '' THEN %s ELSE name END,
                                last_login_at = NOW()
                            WHERE email = %s
                            """,
                            (clean_name, clean_name, norm_email),
                        )
                    else:
                        init_chat_id = initial_chat["chat_id"]
                        cur.execute(
                            """
                            INSERT INTO rag_users (email, name, active_chat_id)
                            VALUES (%s, %s, %s)
                            """,
                            (norm_email, clean_name, init_chat_id),
                        )
                        cur.execute(
                            """
                            INSERT INTO rag_chats (chat_id, user_email, title, pinned)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (init_chat_id, norm_email, initial_chat["title"], False),
                        )
                        for m in initial_chat.get("messages", []):
                            cur.execute(
                                """
                                INSERT INTO rag_messages (
                                    chat_id, role, content, sources, topics, targets,
                                    attached_filename, attached_chars, attached_b2_key,
                                    fallback_used, fallback_reason
                                )
                                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)
                                """,
                                (
                                    init_chat_id,
                                    m.get("role", "assistant"),
                                    m.get("content", ""),
                                    json.dumps(m.get("sources", []), ensure_ascii=False),
                                    json.dumps(m.get("topics", []), ensure_ascii=False),
                                    json.dumps(m.get("targets", []), ensure_ascii=False),
                                    m.get("attached_filename"),
                                    m.get("attached_chars", 0),
                                    m.get("attached_b2_key"),
                                    bool(m.get("fallback_used", False)),
                                    m.get("fallback_reason"),
                                ),
                            )
            return cls.get_user_profile(norm_email)
        except Exception as e:
            logger.error(f"Ошибка регистрации/входа пользователя {norm_email} в Supabase: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_user_profile(cls, email: str) -> Optional[Dict[str, Any]]:
        """Загрузка профиля пользователя со всеми чатами и историей сообщений из Supabase."""
        if not cls.init_schema():
            return None

        norm_email = email.strip().lower()
        conn = None
        try:
            conn = cls._connect()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email, name, active_chat_id FROM rag_users WHERE email = %s",
                    (norm_email,),
                )
                user_row = cur.fetchone()
                if not user_row:
                    return None

                u_email, u_name, active_chat_id = user_row

                cur.execute(
                    """
                    SELECT chat_id, title, pinned, TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI')
                    FROM rag_chats
                    WHERE user_email = %s
                    ORDER BY pinned DESC, updated_at DESC, created_at DESC
                    """,
                    (u_email,),
                )
                chat_rows = cur.fetchall()

                chats: List[Dict[str, Any]] = []
                for c_id, title, pinned, created_str in chat_rows:
                    cur.execute(
                        """
                        SELECT role, content, sources, topics, targets,
                               attached_filename, attached_chars, attached_b2_key,
                               fallback_used, fallback_reason
                        FROM rag_messages
                        WHERE chat_id = %s
                        ORDER BY id ASC
                        """,
                        (c_id,),
                    )
                    msg_rows = cur.fetchall()
                    msgs = []
                    for mr in msg_rows:
                        msgs.append({
                            "role": mr[0],
                            "content": mr[1],
                            "sources": mr[2] or [],
                            "topics": mr[3] or [],
                            "targets": mr[4] or [],
                            "attached_filename": mr[5],
                            "attached_chars": mr[6] or 0,
                            "attached_b2_key": mr[7],
                            "fallback_used": bool(mr[8]),
                            "fallback_reason": mr[9],
                        })

                    chats.append({
                        "chat_id": c_id,
                        "title": title,
                        "created_at": created_str or "",
                        "pinned": bool(pinned),
                        "messages": msgs,
                    })

                if chats and (not active_chat_id or not any(c["chat_id"] == active_chat_id for c in chats)):
                    active_chat_id = chats[0]["chat_id"]

                return {
                    "user_id": u_email,
                    "email": u_email,
                    "user_name": u_name,
                    "active_chat_id": active_chat_id,
                    "chats": chats,
                }
        except Exception as e:
            logger.error(f"Ошибка загрузки профиля {norm_email} из Supabase: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @classmethod
    def list_users(cls) -> List[Dict[str, str]]:
        if not cls.init_schema():
            return []
        conn = None
        try:
            conn = cls._connect()
            with conn.cursor() as cur:
                cur.execute("SELECT email, name FROM rag_users ORDER BY last_login_at DESC LIMIT 50")
                return [{"user_id": r[0], "email": r[0], "user_name": r[1]} for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения списка пользователей Supabase: {e}")
            return []
        finally:
            if conn:
                conn.close()

    @classmethod
    def create_chat(cls, email: str, chat_obj: Dict[str, Any]) -> bool:
        if not cls.init_schema():
            return False
        norm_email = email.strip().lower()
        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    c_id = chat_obj["chat_id"]
                    cur.execute(
                        """
                        INSERT INTO rag_chats (chat_id, user_email, title, pinned)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (chat_id) DO NOTHING
                        """,
                        (c_id, norm_email, chat_obj["title"], bool(chat_obj.get("pinned", False))),
                    )
                    cur.execute(
                        "UPDATE rag_users SET active_chat_id = %s WHERE email = %s",
                        (c_id, norm_email),
                    )
                    for m in chat_obj.get("messages", []):
                        cur.execute(
                            """
                            INSERT INTO rag_messages (chat_id, role, content, sources, topics, targets)
                            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                            """,
                            (
                                c_id,
                                m.get("role", "assistant"),
                                m.get("content", ""),
                                json.dumps(m.get("sources", []), ensure_ascii=False),
                                json.dumps(m.get("topics", []), ensure_ascii=False),
                                json.dumps(m.get("targets", []), ensure_ascii=False),
                            ),
                        )
            return True
        except Exception as e:
            logger.error(f"Ошибка создания чата в Supabase: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def append_message(cls, chat_id: str, msg: Dict[str, Any]) -> bool:
        if not cls.init_schema():
            return False
        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO rag_messages (
                            chat_id, role, content, sources, topics, targets,
                            attached_filename, attached_chars, attached_b2_key,
                            fallback_used, fallback_reason
                        )
                        VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)
                        """,
                        (
                            chat_id,
                            msg.get("role", "user"),
                            msg.get("content", ""),
                            json.dumps(msg.get("sources", []), ensure_ascii=False),
                            json.dumps(msg.get("topics", []), ensure_ascii=False),
                            json.dumps(msg.get("targets", []), ensure_ascii=False),
                            msg.get("attached_filename"),
                            int(msg.get("attached_chars") or 0),
                            msg.get("attached_b2_key"),
                            bool(msg.get("fallback_used", False)),
                            msg.get("fallback_reason"),
                        ),
                    )
                    cur.execute(
                        "UPDATE rag_chats SET updated_at = NOW() WHERE chat_id = %s",
                        (chat_id,),
                    )
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения в Supabase: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def set_active_chat(cls, email: str, chat_id: str) -> bool:
        if not cls.init_schema():
            return False
        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE rag_users SET active_chat_id = %s WHERE email = %s",
                        (chat_id, email.strip().lower()),
                    )
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления active_chat_id: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def toggle_pin(cls, chat_id: str, pinned: bool) -> bool:
        if not cls.init_schema():
            return False
        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE rag_chats SET pinned = %s WHERE chat_id = %s",
                        (pinned, chat_id),
                    )
            return True
        except Exception as e:
            logger.error(f"Ошибка пиннинга чата в Supabase: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def rename_chat(cls, chat_id: str, new_title: str) -> bool:
        if not cls.init_schema():
            return False
        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE rag_chats SET title = %s, updated_at = NOW() WHERE chat_id = %s",
                        (new_title.strip(), chat_id),
                    )
            return True
        except Exception as e:
            logger.error(f"Ошибка переименования чата в Supabase: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def delete_chat(cls, chat_id: str) -> bool:
        if not cls.init_schema():
            return False
        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM rag_chats WHERE chat_id = %s", (chat_id,))
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления чата в Supabase: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def record_document(cls, doc_key: str, user_email: str, chat_id: str, filename: str, size_bytes: int) -> bool:
        if not cls.init_schema():
            return False
        conn = None
        try:
            conn = cls._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO rag_documents (doc_key, user_email, chat_id, filename, size_bytes)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (doc_key) DO NOTHING
                        """,
                        (doc_key, user_email.strip().lower(), chat_id, filename, int(size_bytes)),
                    )
            return True
        except Exception as e:
            logger.error(f"Ошибка записи метаданных документа в Supabase: {e}")
            return False
        finally:
            if conn:
                conn.close()
