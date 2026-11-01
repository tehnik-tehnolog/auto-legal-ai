# Модульный комплекс сбора данных для RAG-ассистента (Раскат машин в РФ)

Комплекс автоматизированного сбора и подготовки базы знаний для RAG-ассистента компании, занимающейся раскатом (арендой с выкупом) автомобилей.

## 🗂 Структура собираемой базы данных

| № | Источник / Раздел | Объем данных | Формат / Структура | Регламент | Назначение в RAG |
|---|-------------------|--------------|--------------------|-----------|------------------|
| 1 | **Нормативная база (ГК РФ)** | ~20 000 статей/пунктов | `.md` файлы с YAML-метаданными (`source_site`, `category`, `original_url`, `title`, `details`, `priority_level`) | Раз в 3 месяца | Гражданско-правовые нормы договоров лизинга, аренды, залога, неустоек. |
| 2 | **Налоговая база (НК РФ)** | Входит в массив законов | `.md` файлы с YAML-метаданными | Раз в 3 месяца | Налоговая нагрузка, баланс ТС, НДС, налог на прибыль. |
| 3 | **Судебная практика ВС РФ** | ~56 документов (2021–2026) | `vsrf_court_docs_rag.json` (`page_content` + `metadata` с датой и номером дела) | Раз в месяц | Позиции Верховного Суда по автоспорам, банкротству, изъятию и раскату. |
| 4 | **Ассортимент машин** | Актуальный каталог | `cars_raskatof.json` + `cars_raskatof_rag.json` (raskatof.ru) | Раз в неделю | Каталог доступных авто, цены, взносы, комплектации, условия. |
| 5 | **Автомобильные новости** | ~50 статей/дайджестов | `latest_autonews.json` (NewsData API + RSS fallback) | Раз в неделю | Мониторинг утильсбора, цен на авто, ОСАГО и изменений законов. |

---

## 🚀 Быстрый запуск на сервере (Ubuntu / Debian)

### Вариант 1. Запуск через Python venv

1. **Клонируйте репозиторий или скопируйте файлы на сервер:**
   ```bash
   mkdir -p /opt/rag_collectors && cd /opt/rag_collectors
   # (скопируйте сюда содержимое папки)
   ```

2. **Установите Python 3.11/3.12 и виртуальное окружение:**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Установите Chromium для Playwright:**
   ```bash
   playwright install chromium
   playwright install-deps chromium
   ```

4. **Проверьте запуск и статус базы:**
   ```bash
   python runner.py --status
   ```

5. **Ручной запуск любого коллектора:**
   ```bash
   # Сбор каталога машин (raskatof.ru):
   python runner.py --collector cars

   # Сбор актуальных автоновостей:
   python runner.py --collector news

   # Сбор судебной практики ВС РФ:
   python runner.py --collector vsrf

   # Сбор нормативной базы (ГК/НК РФ):
   python runner.py --collector laws

   # Запуск всех коллекторов сразу:
   python runner.py --collector all
   ```

---

### Вариант 2. Запуск через Docker & Docker Compose

```bash
# Сборка образа
docker compose build

# Проверка статуса
docker compose run --rm rag-collector python runner.py --status

# Запуск сбора машин
docker compose run --rm rag-collector python runner.py --collector cars
```

---

## ⏰ Настройка автоматического расписания (Cron)

Откройте планировщик cron:
```bash
crontab -e
```

Вставьте следующее расписание:
```cron
# Каждую неделю в понедельник в 04:00 — сбор машин raskatof.ru
0 4 * * 1 cd /opt/rag_collectors && /opt/rag_collectors/venv/bin/python runner.py --collector cars >> logs/cron_cars.log 2>&1

# Каждую неделю в понедельник в 05:00 — сбор новостей
0 5 * * 1 cd /opt/rag_collectors && /opt/rag_collectors/venv/bin/python runner.py --collector news >> logs/cron_news.log 2>&1

# 1-го числа каждого месяца в 03:00 — сбор судебной практики ВС РФ
0 3 1 * * cd /opt/rag_collectors && /opt/rag_collectors/venv/bin/python runner.py --collector vsrf >> logs/cron_vsrf.log 2>&1

# Раз в 3 месяца (1 января, 1 апреля, 1 июля, 1 октября в 02:00) — сбор нормативной базы ГК/НК РФ
0 2 1 1,4,7,10 * cd /opt/rag_collectors && /opt/rag_collectors/venv/bin/python runner.py --collector laws >> logs/cron_laws.log 2>&1
```

---

## 🛠 Что было исправлено по сравнению с исходными скриптами из Colab:

1. **Устранен `TimeoutError` на docs.cntd.ru**:
   - Переход с медленного ожидания `networkidle/load` на `wait_until="domcontentloaded"`.
   - Добавлена блокировка тяжелых баннеров, шрифтов и счетчиков Яндекс.Метрики (`route.abort()`), что ускорило работу в 5 раз.
   - Заменены жесткие Colab-пути (`/content/drive/MyDrive/...`) на гибкую конфигурацию `DATA_DIR`.
   - В YAML-метаданные добавлено поле `priority_level` (`high`, `medium`, `standard`), критичное для ранжирования в RAG.

2. **Судебная практика ВС РФ объединена в единый серверный пайплайн**:
   - Браузер переведен в `headless=True` (ранее стояло `headless=False`, из-за чего скрипт падал на любом Linux-сервере без GUI).
   - Поиск на `vsrf.ru` и скачивание PDF через `PdfReader` объединены в `VSRFCourtCollector` без промежуточных файлов.
   - Добавлено извлечение номера дела и даты из заголовков.
   - Добавлена дедупликация: повторный запуск через месяц не скачивает заново уже сохраненные PDF.

3. **Ассортимент raskatof.ru адаптирован под векторные эмбеддинги RAG**:
   - Помимо сырого JSON сохраняется `cars_raskatof_rag.json` с готовыми текстовыми чанками (`page_content`), оптимизированными для поиска семантического сходства по моделям, суточным ставкам и первому взносу.

4. **Автомобильные новости защищены от падений**:
   - Вынесен API-ключ в переменные окружения.
   - Добавлен автоматический RSS-фоллбэк на российские автомобильные медиа, если исчерпан лимит запросов API.
