"""
Менеджер сессий, профилей пользователей (Email + Имя) и истории чатов для RAG-ассистента.
При работе на Render / в облаке сохраняет все данные в Supabase PostgreSQL (rag_users, rag_chats, rag_messages).
При локальной разработке без Supabase автоматически использует локальные JSON-файлы: data/chats/{user_id}.json.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_pipeline.db_supabase import SupabaseChatDB

logger = logging.getLogger("chat_manager")

BASE_DIR = Path(__file__).resolve().parent.parent
CHATS_DIR = BASE_DIR / "data" / "chats"
CHATS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_USERS = [
    {"user_id": "lawyer_main@company.ru", "user_name": "Юрист компании (Основной)"},
]


def _build_initial_chat() -> Dict[str, Any]:
    initial_chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:21]}"
    return {
        "chat_id": initial_chat_id,
        "title": "Общие вопросы по раскату и законам",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pinned": False,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "Здравствуйте! Я юридический RAG-ассистент компании по раскату автомобилей в РФ.\n\n"
                    "Готов проанализировать правовые вопросы по аренде с выкупом, лизингу, учету расходов, "
                    "налогам (НК РФ), судебной практике ВС РФ и ПДД. Вы можете прикрепить к вопросу документ "
                    "(договор, претензию или иск в формате PDF/DOCX/TXT) с помощью кнопки скрепки справа от поля ввода."
                ),
                "sources": [],
                "topics": [],
                "targets": [],
            }
        ],
    }


class ChatManager:
    """Управление профилями юристов, темами чатов и сохранением истории (Supabase + локальный JSON фоллбэк)"""

    @staticmethod
    def is_cloud_db_active() -> bool:
        return SupabaseChatDB.is_configured()

    @staticmethod
    def get_user_file(user_id: str) -> Path:
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", user_id.strip().lower())
        return CHATS_DIR / f"{safe_id}.json"

    @classmethod
    def register_or_login(cls, email: str, name: str) -> Dict[str, Any]:
        """
        Регистрация нового пользователя (Имя + Email без подтверждения письма)
        или вход существующего пользователя.
        """
        norm_email = email.strip().lower()
        clean_name = name.strip() or norm_email.split("@")[0]
        init_chat = _build_initial_chat()

        if cls.is_cloud_db_active():
            profile = SupabaseChatDB.register_or_login_user(norm_email, clean_name, init_chat)
            if profile:
                return profile
            logger.warning("Не удалось подключиться к Supabase, переключение на локальное хранение JSON.")

        return cls._load_or_create_local_profile(norm_email, clean_name, init_chat)

    @classmethod
    def _load_or_create_local_profile(
        cls, user_id: str, default_name: str = "Юрист", initial_chat: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        user_file = cls.get_user_file(user_id)
        if user_file.exists():
            try:
                with open(user_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "chats" in data:
                        if default_name and default_name != "Юрист" and not data.get("user_name"):
                            data["user_name"] = default_name
                        return data
            except Exception as e:
                logger.error(f"Ошибка загрузки локального профиля {user_id}: {e}")

        chat_obj = initial_chat or _build_initial_chat()
        profile = {
            "user_id": user_id,
            "email": user_id,
            "user_name": default_name,
            "active_chat_id": chat_obj["chat_id"],
            "chats": [chat_obj],
        }
        cls.save_user_profile(profile)
        return profile

    @classmethod
    def load_user_profile(cls, user_id: str, default_name: str = "Юрист") -> Dict[str, Any]:
        norm_id = user_id.strip().lower()
        if cls.is_cloud_db_active():
            profile = SupabaseChatDB.get_user_profile(norm_id)
            if profile:
                if not profile.get("chats"):
                    new_chat = _build_initial_chat()
                    SupabaseChatDB.create_chat(norm_id, new_chat)
                    profile["chats"] = [new_chat]
                    profile["active_chat_id"] = new_chat["chat_id"]
                return profile
            # Если пользователя еще нет в Supabase — регистрируем
            return cls.register_or_login(norm_id, default_name)

        return cls._load_or_create_local_profile(norm_id, default_name)

    @classmethod
    def list_known_users(cls) -> List[Dict[str, str]]:
        if cls.is_cloud_db_active():
            users = SupabaseChatDB.list_users()
            if users:
                return users

        users = []
        for f_path in sorted(CHATS_DIR.glob("*.json")):
            try:
                with open(f_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    users.append({
                        "user_id": d.get("user_id", f_path.stem),
                        "email": d.get("email", d.get("user_id", f_path.stem)),
                        "user_name": d.get("user_name", f_path.stem),
                    })
            except Exception:
                pass
        return users or DEFAULT_USERS

    @classmethod
    def save_user_profile(cls, profile: Dict[str, Any]):
        """Локальное резервное сохранение (в облаке мутации сохраняются точечно в Supabase)"""
        if cls.is_cloud_db_active():
            return
        user_id = profile.get("user_id", "default_user")
        user_file = cls.get_user_file(user_id)
        try:
            with open(user_file, "w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения профиля {user_id}: {e}")

    @classmethod
    def set_active_chat(cls, profile: Dict[str, Any], chat_id: str):
        profile["active_chat_id"] = chat_id
        if cls.is_cloud_db_active():
            SupabaseChatDB.set_active_chat(profile.get("email") or profile.get("user_id", ""), chat_id)
        else:
            cls.save_user_profile(profile)

    @classmethod
    def append_message(cls, profile: Dict[str, Any], chat_id: str, msg: Dict[str, Any]):
        """Добавляет сообщение в чат и сохраняет в Supabase (или локальный JSON)"""
        for chat in profile.get("chats", []):
            if chat.get("chat_id") == chat_id:
                chat.setdefault("messages", []).append(msg)
                break
        if cls.is_cloud_db_active():
            SupabaseChatDB.append_message(chat_id, msg)
        else:
            cls.save_user_profile(profile)

    @classmethod
    def create_new_chat(cls, profile: Dict[str, Any], title: Optional[str] = None) -> str:
        new_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:21]}"
        new_title = title or f"Новый диалог ({datetime.now().strftime('%d.%m %H:%M')})"
        new_chat = {
            "chat_id": new_id,
            "title": new_title,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "pinned": False,
            "messages": [
                {
                    "role": "assistant",
                    "content": "Создан новый чат. Введите вопрос или прикрепите документ для правового анализа.",
                    "sources": [],
                    "topics": [],
                    "targets": [],
                }
            ],
        }
        profile.setdefault("chats", []).insert(0, new_chat)
        profile["active_chat_id"] = new_id
        if cls.is_cloud_db_active():
            SupabaseChatDB.create_chat(profile.get("email") or profile.get("user_id", ""), new_chat)
        else:
            cls.save_user_profile(profile)
        return new_id

    @classmethod
    def toggle_pin(cls, profile: Dict[str, Any], chat_id: str) -> bool:
        for chat in profile.get("chats", []):
            if chat.get("chat_id") == chat_id:
                new_state = not chat.get("pinned", False)
                chat["pinned"] = new_state
                if cls.is_cloud_db_active():
                    SupabaseChatDB.toggle_pin(chat_id, new_state)
                else:
                    cls.save_user_profile(profile)
                return new_state
        return False

    @classmethod
    def delete_chat(cls, profile: Dict[str, Any], chat_id: str) -> bool:
        chats = profile.get("chats", [])
        if len(chats) <= 1:
            return False  # Не удаляем последний чат
        profile["chats"] = [c for c in chats if c.get("chat_id") != chat_id]
        if profile.get("active_chat_id") == chat_id:
            new_active = profile["chats"][0]["chat_id"]
            profile["active_chat_id"] = new_active
            if cls.is_cloud_db_active():
                SupabaseChatDB.set_active_chat(profile.get("email") or profile.get("user_id", ""), new_active)
        if cls.is_cloud_db_active():
            SupabaseChatDB.delete_chat(chat_id)
        else:
            cls.save_user_profile(profile)
        return True

    @classmethod
    def rename_chat(cls, profile: Dict[str, Any], chat_id: str, new_title: str):
        clean_title = new_title.strip()
        if not clean_title:
            return
        for chat in profile.get("chats", []):
            if chat.get("chat_id") == chat_id:
                chat["title"] = clean_title
                if cls.is_cloud_db_active():
                    SupabaseChatDB.rename_chat(chat_id, clean_title)
                else:
                    cls.save_user_profile(profile)
                break

    @classmethod
    def get_active_chat(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        active_id = profile.get("active_chat_id")
        for chat in profile.get("chats", []):
            if chat.get("chat_id") == active_id:
                return chat
        if profile.get("chats"):
            profile["active_chat_id"] = profile["chats"][0]["chat_id"]
            return profile["chats"][0]
        cls.create_new_chat(profile)
        return profile["chats"][0]
