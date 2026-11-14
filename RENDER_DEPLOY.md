# Деплой на Render.com (Free Tier, из GitHub)

Проект подготовлен для работы на **Render.com Free Tier** (без постоянного диска и shell, с засыпанием через 15 минут неактивности):

1. **Профили пользователей и история чатов (Supabase PostgreSQL)**
   - Регистрация новых пользователей выполняется прямо в интерфейсе (Имя + Email без отправки письма-подтверждения).
   - Таблицы (`rag_users`, `rag_chats`, `rag_messages`, `rag_documents`) создаются автоматически при первом запуске приложения — ручные миграции через shell не требуются.
   - Примечание по порту: на Render переменная `PORT` зарезервирована платформой для HTTP-порта веб-сервера (`10000`). В настройках Environment Variables на Render задайте `DB_PORT=6543` (или `SUPABASE_PORT=6543` для Transaction Pooler Supabase) вместе с `HOST`, `USER`, `PASSWORD`.

2. **Хранилище документов (Backblaze B2 Cloud Storage)**
   - Прикрепляемые в чате файлы (`PDF`, `DOCX`, `TXT`) загружаются в S3-совместимый бакет Backblaze B2 (`attachments/{email}/{chat_id}/...`).
   - При необходимости синхронизации базы знаний из B2 на эфемерный контейнер выполните локально один раз:
     ```bash
     python -m rag_pipeline.b2_storage --upload-kb
     ```

3. **Пробуждение при засыпании (`WEBHOOK_BASE_URL`)**
   - При отправке сообщения в чате и при возврате на вкладку браузера отправляется запрос на `WEBHOOK_BASE_URL` (например, `https://<PROJECT-ID>.onrender.com/_stcore/health`).

4. **Подключение GitHub-репозитория в Render**
   - Выберите **New -> Blueprint** (файл `render.yaml` подхватится автоматически) или **New -> Web Service**:
     - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
     - **Start Command:** `sh -c "streamlit run streamlit_app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false"`
   - Заполните Environment Variables: `GEMINI_API_KEY`, `HOST`, `DB_PORT`, `USER`, `PASSWORD`, `B2_ENDPOINT`, `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_REGION`, `B2_BUCKET_NAME`, `WEBHOOK_BASE_URL`.
