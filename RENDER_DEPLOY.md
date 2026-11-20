# Деплой на Render.com (Node.js + React)

Приложение работает как единый сервис **Express (Node.js) + React** и подготовлено для **Render.com Free Tier** (без постоянного диска и shell, с засыпанием через 15 минут неактивности):

1. **Профили пользователей, гостевой вход и история чатов (Supabase PostgreSQL)**
   - Регистрация выполняется по имени и email (без отправки письма-подтверждения) или через кнопку **«Войти как гость»**.
   - Устройство запоминается по токену для автоматического повторного входа.
   - Таблицы (`rag_users`, `rag_chats`, `rag_messages`, `rag_documents`) создаются автоматически при первом запуске сервера.
   - На Render задайте `DB_PORT=6543` (или `SUPABASE_PORT=6543` для Transaction Pooler Supabase) вместе с `HOST`, `USER`, `PASSWORD`.

2. **Хранение базы знаний `data/` и вложений в Backblaze B2 Storage**
   - Каталог `data/` исключён из Git (`.gitignore`), чтобы не загружать ~100 МБ файлов в репозиторий, и хранится в бакете **Backblaze B2** под префиксом `kb/`.
   - Однократно загрузите локальную папку `data/` (`legal`, `pdd`, `court`, `news`, `cars`, `chroma`) в бакет Backblaze B2:
     ```bash
     npm run b2:upload
     ```
   - При старте контейнера на Render сервер проверяет наличие ключевых файлов базы знаний (`data/legal/legal_chapters.jsonl`, `data/pdd/pdd_chapters.jsonl`, `data/chroma/legal_laws_chunks.json`, `data/chroma/parent_store.json`) и автоматически скачивает их из Backblaze B2 (либо при `B2_AUTO_SYNC=true`).
   - Локально принудительно скачать базу из бакета можно командой:
     ```bash
     npm run b2:sync
     ```
   - Прикрепляемые в чате файлы (`PDF`, `DOCX`, `TXT`) сохраняются в `attachments/{email}/{chat_id}/...`.

3. **Пробуждение при засыпании (`WEBHOOK_BASE_URL`)**
   - При отправке сообщения в чате и при возврате на вкладку браузера отправляется запрос на `/api/health` и `WEBHOOK_BASE_URL` (например, `https://<PROJECT-ID>.onrender.com`).

4. **Подключение GitHub-репозитория в Render**
   - Выберите **New -> Blueprint** (файл `render.yaml` подхватится автоматически) или **New -> Web Service**:
     - **Runtime:** `Node`
     - **Build Command:** `npm install && npm run build`
     - **Start Command:** `npm run start`
     - **Health Check Path:** `/api/health`
   - Заполните Environment Variables: `GEMINI_API_KEY`, `HOST`, `DB_PORT`, `USER`, `PASSWORD`, `B2_ENDPOINT`, `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_REGION`, `B2_BUCKET_NAME`, `WEBHOOK_BASE_URL`.
