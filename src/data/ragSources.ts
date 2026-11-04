export interface RAGSource {
  id: string;
  number: number;
  name: string;
  section: string;
  volume: string;
  format: string;
  schedule: string;
  scheduleCron: string;
  ragPurpose: string;
  collectorName: string;
  collectorFile: string;
  status: 'ready' | 'active' | 'scheduled';
  sampleFile: string;
  sampleContent: string;
  keyFields: string[];
}

export const RAG_SOURCES: RAGSource[] = [
  {
    id: 'gk',
    number: 1,
    name: 'Нормативная база (ГК РФ)',
    section: 'Гражданский кодекс РФ',
    volume: '~20 000 документов (статьи/пункты)',
    format: 'Единый JSONL файл (laws_gk_nk.jsonl)',
    schedule: 'Раз в 3 месяца',
    scheduleCron: '0 2 1 1,4,7,10 *',
    ragPurpose: 'Базовые гражданско-правовые нормы договоров лизинга, аренды, залога и обязательств.',
    collectorName: 'LawsCollector (ГК/КоАП/Законы)',
    collectorFile: 'collectors/gk_nk_laws.py',
    status: 'ready',
    sampleFile: 'data/legal/laws_gk_nk.jsonl',
    keyFields: ['parent_id', 'source_site', 'section', 'category', 'original_url', 'title', 'details', 'collected_at'],
    sampleContent: `{
  "parent_id": "civics_d396fcf3_82cb62fe",
  "source_site": "docs.cntd.ru",
  "section": "ГК РФ",
  "category": "Гражданский кодекс РФ",
  "original_url": "https://docs.cntd.ru/document/9027703",
  "title": "ГРАЖДАНСКИЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ЧАСТЬ ВТОРАЯ (с изменениями на 9 июня 2026 года)",
  "details": "Федеральный закон от 26 января 1996 года № 14-ФЗ (Аренда, Лизинг гл. 34)",
  "collected_at": "2026-11-04 12:00:00",
  "priority_level": "high",
  "body": "Статья 624 ГК РФ: Выкуп арендованного имущества (раскат авто). Статья 642 ГК РФ: Аренда транспортного средства без экипажа. Статья 665 ГК РФ: Финансовая аренда (лизинг автомобилей)..."
}`
  },
  {
    id: 'nk',
    number: 2,
    name: 'Налоговая база (НК РФ)',
    section: 'Налоговый кодекс РФ',
    volume: 'Входит в единый JSONL массив 14 законов',
    format: 'Единый JSONL файл (laws_gk_nk.jsonl)',
    schedule: 'Раз в 3 месяца',
    scheduleCron: '0 2 1 1,4,7,10 *',
    ragPurpose: 'Расчет налоговой нагрузки, учет транспортных средств на балансе, лизинговые платежи, НДС, налог на прибыль.',
    collectorName: 'LawsCollector (НК)',
    collectorFile: 'collectors/gk_nk_laws.py',
    status: 'ready',
    sampleFile: 'data/legal/laws_gk_nk.jsonl',
    keyFields: ['parent_id', 'source_site', 'section', 'category', 'original_url', 'title', 'details', 'collected_at'],
    sampleContent: `{
  "parent_id": "tax_9e1b402c_8a5f1109",
  "source_site": "docs.cntd.ru",
  "section": "НК РФ",
  "category": "Налоговый кодекс РФ",
  "original_url": "https://docs.cntd.ru/document/901765862",
  "title": "НАЛОГОВЫЙ КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ЧАСТЬ ВТОРАЯ (с изменениями на 4 августа 2026 года)",
  "details": "Федеральный закон от 5 августа 2000 года № 117-ФЗ (Транспортный налог гл. 28, НДС, Прибыль)",
  "collected_at": "2026-11-04 12:00:00",
  "priority_level": "high",
  "body": "Глава 28 НК РФ регламентирует транспортный налог. Плательщиком транспортного налога признается лицо, на которое зарегистрировано ТС в ГИБДД. Статья 264 НК РФ: учет лизинговых платежей за авто в составе прочих расходов..."
}`
  },
  {
    id: 'vsrf',
    number: 3,
    name: 'Судебная практика ВС РФ',
    section: 'Верховный Суд Российской Федерации',
    volume: '56 документов (2021–2026 гг., «автомобиль»)',
    format: 'vsrf_court_docs_rag.json (page_content + metadata)',
    schedule: 'Раз в месяц',
    scheduleCron: '0 3 1 * *',
    ragPurpose: 'Анализ позиций Верховного Суда по спорам о защите прав потребителей, банкротстве и имуществу.',
    collectorName: 'VSRFCourtCollector',
    collectorFile: 'collectors/vsrf_court.py',
    status: 'ready',
    sampleFile: 'data/court/vsrf_court_docs_rag.json',
    keyFields: ['page_content', 'metadata.case_number', 'metadata.date', 'metadata.url', 'metadata.doc_type'],
    sampleContent: `[
  {
    "page_content": "Заголовок: Определение Судебной коллегии по гражданским делам ВС РФ № 5-КГ23-104-К2\\nНомер дела: 5-КГ23-104-К2\\nДата: 14.11.2023\\nТекст постановления:\\nСудебная коллегия по гражданским делам Верховного Суда Российской Федерации рассмотрела кассационную жалобу по спору о расторжении договора аренды транспортного средства с правом выкупа... Коллегия указала: при систематическом нарушении графика внесения арендных платежей арендодатель вправе истребовать предмет лизинга (автомобиль) из незаконного владения, при этом сальдо взаимных обязательств подлежит расчету с учетом амортизации и фактического износа транспортного средства.",
    "metadata": {
      "title": "Определение Судебной коллегии по гражданским делам ВС РФ № 5-КГ23-104-К2",
      "case_number": "5-КГ23-104-К2",
      "date": "14.11.2023",
      "url": "https://www.vsrf.ru/media-proxy/?id=228419",
      "source": "vsrf.ru",
      "doc_type": "court_decision",
      "category": "Судебная практика ВС РФ (автомобили/лизинг)",
      "char_length": 18450,
      "collected_at": "2026-11-01 03:15:22"
    }
  }
]`
  },
  {
    id: 'cars',
    number: 4,
    name: 'Ассортимент машин',
    section: 'Каталог raskatof.ru',
    volume: 'Актуальный автопарк в наличии',
    format: 'Структурированные карточки (cars_raskatof.json + RAG)',
    schedule: 'Раз в неделю',
    scheduleCron: '0 4 * * 1',
    ragPurpose: 'Актуальный каталог доступных для аренды/выкупа автомобилей, комплектации, цены и условия.',
    collectorName: 'CarsCollector',
    collectorFile: 'collectors/raskatof_cars.py',
    status: 'ready',
    sampleFile: 'data/cars/cars_raskatof.json',
    keyFields: ['category', 'model', 'specifications', 'features', 'leasing_terms', 'page_content'],
    sampleContent: `[
  {
    "category": "Эконом и комфорт класс",
    "model": "Chery Tiggo 4 Pro (1.5 CVT)",
    "specifications": {
      "Год выпуска": "2023",
      "Мощность": "113 л.с.",
      "Коробка передач": "Вариатор (CVT)",
      "Топливо": "Бензин (АИ-92)"
    },
    "features": [
      "Камера заднего вида и парктроники",
      "Круиз-контроль",
      "Обогрев передних сидений и руля",
      "Мультимедиа 10.25 дюйма с Apple CarPlay / Android Auto"
    ],
    "leasing_terms": {
      "daily_rate": "Аренда от 2 400 ₽ / сутки",
      "initial_payment": "Первоначальный взнос 15 000 ₽"
    },
    "source_url": "https://raskatof.ru/",
    "updated_at": "2026-11-01 04:00:32"
  }
]`
  },
  {
    id: 'news',
    number: 5,
    name: 'Автомобильные новости',
    section: 'Отраслевые автоновости и регуляторика',
    volume: '50 коротких статей / дайджестов',
    format: 'Текстовые статьи с датами (latest_autonews.json)',
    schedule: 'Раз в неделю',
    scheduleCron: '0 5 * * 1',
    ragPurpose: 'Мониторинг изменений рынка, цен на авто и законодательных инициатив в сфере транспорта.',
    collectorName: 'AutoNewsCollector',
    collectorFile: 'collectors/auto_news.py',
    status: 'ready',
    sampleFile: 'data/news/latest_autonews.json',
    keyFields: ['page_content', 'metadata.title', 'metadata.url', 'metadata.date', 'metadata.source'],
    sampleContent: `[
  {
    "page_content": "Заголовок: Индексация утилизационного сбора и ее влияние на лизинг коммерческих и легковых авто\\nСодержание: Правительство РФ утвердило шкалу плановой индексации утильсбора до 2030 года. Для парков раската и лизинговых компаний повышение ставок означает рост первоначальной стоимости приобретаемых транспортных средств в среднем на 12-18% в зависимости от объема двигателя. Эксперты отмечают смещение спроса в сторону локализованных брендов и автомобилей с пробегом до 3 лет.",
    "metadata": {
      "title": "Индексация утилизационного сбора и ее влияние на лизинг",
      "url": "https://autonews.ru/news/util-sbor-leasing-impact-2026",
      "date": "2026-10-28T14:20:00Z",
      "source": "autonews.ru",
      "matched_query": "утильсбор",
      "is_full_text": true,
      "collected_at": "2026-11-01 05:01:10"
    }
  }
]`
  },
  {
    id: 'pdd',
    number: 6,
    name: 'Правила дорожного движения (ПДД РФ)',
    section: 'ГИБДД РФ / ПДД',
    volume: '19 смысловых разделов (абзацы)',
    format: 'Абзацный JSON (pdd_rules_rag.json)',
    schedule: 'По мере изменений ПДД',
    scheduleCron: '0 4 1 * *',
    ragPurpose: 'Обязанности водителя, правила перевозки детей, скоростные режимы, фиксация ДТП, перечень неисправностей.',
    collectorName: 'PDDCollector (ГИБДД PDF)',
    collectorFile: 'collectors/pdd.py',
    status: 'ready',
    sampleFile: 'data/pdd/pdd_rules_rag.json',
    keyFields: ['section_number', 'section_title', 'clause_number', 'paragraph_text', 'topic'],
    sampleContent: `[
  {
    "section_number": 2,
    "section_title": "2. Общие обязанности водителей",
    "clause_number": "2.1.1",
    "paragraph_text": "Водитель механического ТС обязан иметь при себе: водительское удостоверение, регистрационные документы (СТС), полис ОСАГО...",
    "topic": "Документы водителя и полис ОСАГО"
  }
]`
  }
];

export const SERVER_SCRIPTS = [
  {
    path: 'streamlit_app.py',
    name: 'streamlit_app.py',
    badge: 'Streamlit Web UI',
    description: 'Интерфейс веб-приложения на Streamlit: RAG-чат, каталог авто, база законов и судебной практики'
  },
  {
    path: 'run_streamlit.bat',
    name: 'run_streamlit.bat',
    badge: 'Windows Bat',
    description: 'Запуск веб-приложения Streamlit на Windows 10 одним кликом'
  },
  {
    path: 'run_collectors.bat',
    name: 'run_collectors.bat',
    badge: 'Windows Bat',
    description: 'Запуск сбора данных на Windows 10 через виртуальное окружение PyCharm / venv'
  },
  {
    path: 'setup_windows_scheduler.bat',
    name: 'setup_windows_scheduler.bat',
    badge: 'Task Scheduler',
    description: 'Автоматическое добавление 4 заданий сбора данных в Планировщик заданий Windows 10'
  },
  {
    path: 'runner.py',
    name: 'runner.py',
    badge: 'CLI Entrypoint',
    description: 'Мастер-скрипт оркестрации с поддержкой Windows 10 Proactor asyncio, cron и проверки базы'
  },
  {
    path: 'collectors/gk_nk_laws.py',
    name: 'collectors/gk_nk_laws.py',
    badge: 'ГК РФ / НК РФ',
    description: 'Сбор нормативно-правовых актов с docs.cntd.ru без таймаутов, с YAML frontmatter и priority_level'
  },
  {
    path: 'collectors/vsrf_court.py',
    name: 'collectors/vsrf_court.py',
    badge: 'ВС РФ (PDF)',
    description: 'Headless сбор определений ВС РФ по автоспорам с извлечением текста из PDF и дедупликацией'
  },
  {
    path: 'collectors/raskatof_cars.py',
    name: 'collectors/raskatof_cars.py',
    badge: 'raskatof.ru',
    description: 'Сбор каталога авто, условий раската/выкупа и формирование RAG-чанков'
  },
  {
    path: 'collectors/auto_news.py',
    name: 'collectors/auto_news.py',
    badge: 'Новости авторынка',
    description: 'Сбор новостей по утильсбору, лизингу и ОСАГО через NewsData API с RSS-фоллбэком'
  },
  {
    path: 'config/settings.py',
    name: 'config/settings.py',
    badge: 'Настройки',
    description: 'Централизованная конфигурация путей, тайм-аутов, URL и API-ключей'
  },
  {
    path: 'requirements.txt',
    name: 'requirements.txt',
    badge: 'Зависимости',
    description: 'Пакеты: streamlit, pandas, playwright, requests, beautifulsoup4, pypdf, pyyaml'
  },
  {
    path: 'Dockerfile',
    name: 'Dockerfile',
    badge: 'Docker',
    description: 'Контейнер со всеми системными библиотеками Chromium для headless запуска в Docker Desktop / WSL2'
  }
];
