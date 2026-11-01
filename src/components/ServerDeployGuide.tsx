import React, { useState } from 'react';
import { 
  Server, 
  Terminal, 
  Clock, 
  Check, 
  Copy, 
  AlertTriangle, 
  Sparkles, 
  ShieldCheck, 
  ExternalLink,
  Layers,
  CheckCircle2,
  Cpu,
  Monitor
} from 'lucide-react';

export const ServerDeployGuide: React.FC = () => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const copyToClipboard = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const codeSnippets = [
    // 0: PyCharm setup
    `# 1. Откройте проект в PyCharm: File -> Open -> Выберите папку проекта

# 2. В терминале PyCharm (Alt+F12) установите зависимости:
pip install -r requirements.txt

# 3. Установите браузер Chromium для Playwright:
playwright install chromium`,

    // 1: Run Streamlit
    `# Запуск веб-части на Streamlit (откроется в браузере http://localhost:8501):
streamlit run streamlit_app.py

# Или двойным кликом по батнику в папке проекта:
run_streamlit.bat`,

    // 2: Test collectors
    `# Ручной тестовый запуск коллекторов на Windows 10:
run_collectors.bat status   # Проверить количество файлов в data/
run_collectors.bat cars     # Собрать каталог raskatof.ru (еженедельно)
run_collectors.bat news     # Собрать автоновости (еженедельно)
run_collectors.bat vsrf     # Собрать практику ВС РФ (ежемесячно)
run_collectors.bat laws     # Собрать статьи ГК/НК РФ (раз в 3 мес)`,

    // 3: Windows Task Scheduler
    `# Запустите командную строку (cmd) ОТ ИМЕНИ АДМИНИСТРАТОРА и выполните:
setup_windows_scheduler.bat

# Либо вручную через schtasks:
schtasks /create /tn "RAG_Collector_Cars" /tr "\\"%CD%\\run_collectors.bat\\" cars" /sc weekly /d MON /st 04:00 /f
schtasks /create /tn "RAG_Collector_News" /tr "\\"%CD%\\run_collectors.bat\\" news" /sc weekly /d MON /st 05:00 /f
schtasks /create /tn "RAG_Collector_VSRF" /tr "\\"%CD%\\run_collectors.bat\\" vsrf" /sc monthly /d 1 /st 03:00 /f
schtasks /create /tn "RAG_Collector_Laws" /tr "\\"%CD%\\run_collectors.bat\\" laws" /sc monthly /m JAN,APR,JUL,OCT /d 1 /st 02:00 /f`,

    // 4: Docker / WSL2
    `# Запуск через Docker Desktop на Windows 10 (WSL2):
docker compose build

# Тестовый сбор данных в контейнере:
docker compose run --rm rag-collector python runner.py --collector cars

# Проверка файлов в общей папке data/:
docker compose run --rm rag-collector python runner.py --status`
  ];

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="p-6 bg-gradient-to-br from-blue-600/10 via-blue-600/5 to-transparent border border-blue-600/20 rounded-2xl space-y-2">
        <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 font-semibold text-xs uppercase tracking-wider">
          <Monitor className="w-4 h-4" />
          <span>Среда: Windows 10 + PyCharm + Планировщик заданий / Docker / WSL2</span>
        </div>
        <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
          Архитектура: Streamlit (Веб) + Сервер сбора (Windows 10)
        </h2>
        <p className="text-xs sm:text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed max-w-3xl">
          Проект разделен на две взаимосвязанные части, работающие с общей директорией <code>data/</code>:
          интерактивный веб-интерфейс на **Streamlit** и автоматический сервер сбора данных по расписанию в **Windows Task Scheduler** или Docker.
        </p>
      </div>

      {/* Architecture Diagram */}
      <div className="p-6 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-4 shadow-xs">
        <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
          <Layers className="w-5 h-5 text-blue-600" />
          <span>Схема взаимодействия веб-части и серверного сбора данных:</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-4 bg-blue-50/60 dark:bg-blue-950/20 border border-blue-200/80 dark:border-blue-900/40 rounded-xl space-y-2">
            <span className="font-bold text-blue-900 dark:text-blue-300 block font-sans">
              1. Сервер сбора (Windows 10)
            </span>
            <p className="text-blue-800 dark:text-blue-300 text-[11px] font-sans leading-relaxed">
              Работает в фоне по расписанию через <strong>Планировщик заданий Windows</strong>:
            </p>
            <ul className="space-y-1 text-blue-700 dark:text-blue-400 text-[11px]">
              <li>• raskatof.ru (пн, 04:00)</li>
              <li>• Автоновости (пн, 05:00)</li>
              <li>• ВС РФ (1-е число, 03:00)</li>
              <li>• ГК/НК РФ (1 раз в 3 мес)</li>
            </ul>
          </div>

          <div className="p-4 bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200/80 dark:border-emerald-900/40 rounded-xl space-y-2">
            <span className="font-bold text-emerald-900 dark:text-emerald-300 block font-sans">
              2. Общее хранилище (data/)
            </span>
            <p className="text-emerald-800 dark:text-emerald-300 text-[11px] font-sans leading-relaxed">
              Структурированная база знаний RAG:
            </p>
            <ul className="space-y-1 text-emerald-700 dark:text-emerald-400 text-[11px]">
              <li>📁 data/cars/cars_raskatof.json</li>
              <li>📁 data/court/vsrf_court_docs.json</li>
              <li>📁 data/news/latest_autonews.json</li>
              <li>📁 data/legal/*.md (YAML frontmatter)</li>
            </ul>
          </div>

          <div className="p-4 bg-purple-50/60 dark:bg-purple-950/20 border border-purple-200/80 dark:border-purple-900/40 rounded-xl space-y-2">
            <span className="font-bold text-purple-900 dark:text-purple-300 block font-sans">
              3. Веб-интерфейс (Streamlit)
            </span>
            <p className="text-purple-800 dark:text-purple-300 text-[11px] font-sans leading-relaxed">
              <code>streamlit run streamlit_app.py</code>
            </p>
            <ul className="space-y-1 text-purple-700 dark:text-purple-400 text-[11px]">
              <li>💬 Чат RAG-ассистента</li>
              <li>🚙 Витрина авто raskatof.ru</li>
              <li>⚖️ Поиск решений ВС РФ</li>
              <li>📜 База статей ГК и НК РФ</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Step by Step Deployment for Windows 10 & PyCharm */}
      <div className="space-y-6">
        <h3 className="text-lg font-bold text-neutral-900 dark:text-neutral-100">
          Пошаговая инструкция для Windows 10 и PyCharm:
        </h3>

        {/* Step 1: PyCharm & venv */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-blue-600 text-white font-bold text-xs flex items-center justify-center font-mono">
                1
              </span>
              <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Настройка окружения в PyCharm
              </h4>
            </div>
            <button
              onClick={() => copyToClipboard(codeSnippets[0], 0)}
              className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-200"
            >
              {copiedIndex === 0 ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedIndex === 0 ? 'Скопировано!' : 'Копировать'}</span>
            </button>
          </div>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            Распакуйте архив в папку проекта и откройте ее в PyCharm. В терминале PyCharm выполните установку библиотек и Playwright:
          </p>
          <div className="p-3 bg-[#0E1117] text-neutral-200 rounded-lg font-mono text-xs overflow-x-auto">
            <pre>{codeSnippets[0]}</pre>
          </div>
        </div>

        {/* Step 2: Run Streamlit */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-blue-600 text-white font-bold text-xs flex items-center justify-center font-mono">
                2
              </span>
              <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Запуск веб-интерфейса Streamlit
              </h4>
            </div>
            <button
              onClick={() => copyToClipboard(codeSnippets[1], 1)}
              className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-200"
            >
              {copiedIndex === 1 ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedIndex === 1 ? 'Скопировано!' : 'Копировать'}</span>
            </button>
          </div>
          <div className="p-3 bg-[#0E1117] text-neutral-200 rounded-lg font-mono text-xs overflow-x-auto">
            <pre>{codeSnippets[1]}</pre>
          </div>
        </div>

        {/* Step 3: Manual test of collectors */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-blue-600 text-white font-bold text-xs flex items-center justify-center font-mono">
                3
              </span>
              <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Пробный запуск сбора данных через run_collectors.bat
              </h4>
            </div>
            <button
              onClick={() => copyToClipboard(codeSnippets[2], 2)}
              className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-200"
            >
              {copiedIndex === 2 ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedIndex === 2 ? 'Скопировано!' : 'Копировать'}</span>
            </button>
          </div>
          <div className="p-3 bg-[#0E1117] text-neutral-200 rounded-lg font-mono text-xs overflow-x-auto">
            <pre>{codeSnippets[2]}</pre>
          </div>
        </div>

        {/* Step 4: Windows Task Scheduler */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-blue-600 text-white font-bold text-xs flex items-center justify-center font-mono">
                4
              </span>
              <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Автоматическое расписание в Планировщике заданий Windows 10
              </h4>
            </div>
            <button
              onClick={() => copyToClipboard(codeSnippets[3], 3)}
              className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-200"
            >
              {copiedIndex === 3 ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedIndex === 3 ? 'Скопировано!' : 'Копировать'}</span>
            </button>
          </div>
          <p className="text-xs text-neutral-600 dark:text-neutral-400">
            Скрипт автоматически создаст 4 фоновые задачи сбора в Windows Task Scheduler. Запустите <code>setup_windows_scheduler.bat</code> от имени Администратора:
          </p>
          <div className="p-3 bg-[#0E1117] text-neutral-200 rounded-lg font-mono text-xs overflow-x-auto">
            <pre>{codeSnippets[3]}</pre>
          </div>
        </div>

        {/* Step 5: Docker / WSL2 */}
        <div className="p-5 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-neutral-800 text-white font-bold text-xs flex items-center justify-center font-mono">
                🐳
              </span>
              <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                Вариант запуска через Docker Desktop / WSL2
              </h4>
            </div>
            <button
              onClick={() => copyToClipboard(codeSnippets[4], 4)}
              className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-200"
            >
              {copiedIndex === 4 ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedIndex === 4 ? 'Скопировано!' : 'Копировать'}</span>
            </button>
          </div>
          <div className="p-3 bg-[#0E1117] text-neutral-200 rounded-lg font-mono text-xs overflow-x-auto">
            <pre>{codeSnippets[4]}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};
