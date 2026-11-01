import React, { useState, useEffect } from 'react';
import { 
  X, 
  Play, 
  Terminal, 
  CheckCircle2, 
  RotateCw, 
  AlertCircle, 
  Download,
  ShieldCheck,
  Check
} from 'lucide-react';

interface CollectorRunnerModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialCollector: string;
}

export const CollectorRunnerModal: React.FC<CollectorRunnerModalProps> = ({
  isOpen,
  onClose,
  initialCollector
}) => {
  const [selectedCollector, setSelectedCollector] = useState(initialCollector || 'cars');
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const [collectedCount, setCollectedCount] = useState(0);

  useEffect(() => {
    if (initialCollector) {
      setSelectedCollector(initialCollector);
    }
  }, [initialCollector]);

  if (!isOpen) return null;

  const startSimulation = () => {
    setIsRunning(true);
    setIsCompleted(false);
    setProgress(5);
    setLogs([
      `[INFO] [runner] Запуск команды: python runner.py --collector ${selectedCollector}`,
      `[INFO] [settings] RAG_DATA_DIR: /app/data`,
      `[INFO] [settings] Проверка системных библиотек Playwright Chromium... [OK]`
    ]);

    const logSequence: { text: string; delay: number; prog: number }[] = [];

    if (selectedCollector === 'cars') {
      logSequence.push(
        { text: '[INFO] [raskatof_cars] === Запуск коллектора [raskatof_cars] ===', delay: 400, prog: 20 },
        { text: '[INFO] [raskatof_cars] Запрос каталога авто с https://raskatof.ru/...', delay: 800, prog: 40 },
        { text: '[INFO] [raskatof_cars] HTTP 200 OK. Найдено блоков с автомобилями: 19', delay: 1200, prog: 60 },
        { text: '[INFO] [raskatof_cars] Парсинг: Chery Tiggo 4 Pro, Haval Jolion, Geely Coolray...', delay: 1600, prog: 75 },
        { text: '[INFO] [raskatof_cars] Генерация структурных RAG-чанков (модели, взносы, ставки)...', delay: 2000, prog: 90 },
        { text: '[INFO] [raskatof_cars] Сохранено в data/cars/cars_raskatof.json (19 авто)', delay: 2300, prog: 95 },
        { text: '[INFO] [raskatof_cars] [SUCCESS] Коллектор [raskatof_cars] завершен. Собрано: 19 объектов.', delay: 2500, prog: 100 }
      );
    } else if (selectedCollector === 'news') {
      logSequence.push(
        { text: '[INFO] [auto_news] === Запуск коллектора [auto_news] ===', delay: 400, prog: 20 },
        { text: '[INFO] [auto_news] Запрос к NewsData API по запросам: "утильсбор", "лизинг", "раскат"...', delay: 800, prog: 45 },
        { text: '[INFO] [auto_news] Найдено 32 статьи в NewsData API. Обработка полного текста...', delay: 1300, prog: 65 },
        { text: '[INFO] [auto_news] Подключение резервных RSS-лент (Autonews / Motor.ru) для полноты...', delay: 1800, prog: 80 },
        { text: '[INFO] [auto_news] Очистка кодировок (mojibake) и фильтрация стоп-слов...', delay: 2200, prog: 90 },
        { text: '[INFO] [auto_news] Сохранено в data/news/latest_autonews.json (50 статей)', delay: 2500, prog: 95 },
        { text: '[INFO] [auto_news] [SUCCESS] Коллектор [auto_news] завершен. Собрано: 50 объектов.', delay: 2700, prog: 100 }
      );
    } else if (selectedCollector === 'vsrf') {
      logSequence.push(
        { text: '[INFO] [vsrf_court] === Запуск коллектора [vsrf_court] ===', delay: 400, prog: 15 },
        { text: '[INFO] [vsrf_court] Запуск Chromium в режиме headless=True (Linux headless)...', delay: 800, prog: 30 },
        { text: '[INFO] [vsrf_court] Переход на https://www.vsrf.ru/documents... [OK]', delay: 1200, prog: 45 },
        { text: '[INFO] [vsrf_court] Установка поискового слова "автомобиль" и годов 2021-2026...', delay: 1600, prog: 60 },
        { text: '[INFO] [vsrf_court] Найдено 56 уникальных постановлений ВС РФ в PDF...', delay: 2100, prog: 75 },
        { text: '[INFO] [vsrf_court] Потоковое извлечение текста через PdfReader без падений...', delay: 2600, prog: 85 },
        { text: '[INFO] [vsrf_court] Формирование metadata с номером дела и датой суда...', delay: 3000, prog: 95 },
        { text: '[INFO] [vsrf_court] [SUCCESS] Сохранено в data/court/vsrf_court_docs_rag.json (56 документов)', delay: 3300, prog: 100 }
      );
    } else {
      // laws
      logSequence.push(
        { text: '[INFO] [laws_gk_nk] === Запуск коллектора [laws_gk_nk] ===', delay: 400, prog: 15 },
        { text: '[INFO] [laws_gk_nk] Запуск Chromium с блокировкой картинок, шрифтов и метрик (ускорение x5)...', delay: 900, prog: 35 },
        { text: '[INFO] [laws_gk_nk] Переход на каталог docs.cntd.ru (wait_until=domcontentloaded)...', delay: 1400, prog: 55 },
        { text: '[INFO] [laws_gk_nk] Успешный обход TimeoutError! Документы каталога загружены.', delay: 1900, prog: 70 },
        { text: '[INFO] [laws_gk_nk] Применение фильтра: лизинг, прокат, аренда ТС, залог, НДС...', delay: 2400, prog: 85 },
        { text: '[INFO] [laws_gk_nk] Сохранение .md файлов с YAML frontmatter и priority_level...', delay: 2900, prog: 95 },
        { text: '[INFO] [laws_gk_nk] [SUCCESS] Нормативная база ГК/НК РФ успешно обновлена.', delay: 3200, prog: 100 }
      );
    }

    logSequence.forEach((step, idx) => {
      setTimeout(() => {
        setLogs(prev => [...prev, step.text]);
        setProgress(step.prog);
        if (idx === logSequence.length - 1) {
          setIsRunning(false);
          setIsCompleted(true);
          setCollectedCount(selectedCollector === 'cars' ? 19 : selectedCollector === 'news' ? 50 : selectedCollector === 'vsrf' ? 56 : 1420);
        }
      }, step.delay);
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div className="relative w-full max-w-3xl bg-white dark:bg-[#12161E] rounded-2xl border border-neutral-200 dark:border-neutral-800 shadow-2xl p-6 md:p-8 max-h-[90vh] flex flex-col">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-5 top-5 p-1.5 text-neutral-400 hover:text-neutral-900 dark:hover:text-white rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="pr-10 space-y-1">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
            <Terminal className="w-3.5 h-3.5" />
            <span>Интерактивный тест серверного скрипта</span>
          </div>
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
            Эмуляция запуска runner.py на сервере
          </h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Проверка логики сбора, обработки ошибок и генерации файлов базы RAG
          </p>
        </div>

        {/* Collector Selector Bar */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
            Выбор коллектора:
          </label>
          <div className="flex flex-wrap gap-1.5">
            {[
              { id: 'cars', label: '🚗 raskatof.ru (Автопарк)' },
              { id: 'news', label: '📰 Автоновости' },
              { id: 'vsrf', label: '⚖️ ВС РФ (Суд)' },
              { id: 'laws', label: '📜 ГК / НК РФ' }
            ].map(col => (
              <button
                key={col.id}
                disabled={isRunning}
                onClick={() => {
                  setSelectedCollector(col.id);
                  setLogs([]);
                  setIsCompleted(false);
                }}
                className={`px-2.5 py-1 text-xs font-medium rounded-md border transition-colors ${
                  selectedCollector === col.id
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-200'
                }`}
              >
                {col.label}
              </button>
            ))}
          </div>

          <button
            onClick={startSimulation}
            disabled={isRunning}
            className="ml-auto px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.98] rounded-lg transition-all flex items-center gap-1.5 shadow-xs disabled:opacity-50"
          >
            {isRunning ? (
              <RotateCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
            <span>{isRunning ? 'Выполняется...' : 'Запустить тест'}</span>
          </button>
        </div>

        {/* Progress Bar */}
        {isRunning && (
          <div className="mt-3 w-full bg-neutral-200 dark:bg-neutral-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-blue-600 h-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}

        {/* Terminal Logs Window */}
        <div className="mt-4 flex-1 flex flex-col min-h-[260px] max-h-[380px] bg-[#0A0D12] border border-neutral-800 rounded-xl overflow-hidden font-mono text-xs">
          <div className="flex items-center justify-between px-4 py-2 bg-[#12161F] border-b border-neutral-800 text-neutral-400">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
              <span className="ml-2 text-[11px] text-neutral-400">bash - server shell</span>
            </div>
            <span className="text-[11px] text-neutral-500">
              {logs.length} строк
            </span>
          </div>

          <div className="flex-1 p-4 overflow-y-auto space-y-1.5 text-neutral-300">
            {logs.length === 0 ? (
              <div className="text-neutral-500 italic py-8 text-center">
                Нажмите «Запустить тест», чтобы просимулировать работу серверного коллектора с выводом реальных логов.
              </div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="leading-5">
                  <span className={log.includes('[SUCCESS]') ? 'text-emerald-400 font-bold' : log.includes('[ERROR]') ? 'text-red-400 font-bold' : 'text-neutral-300'}>
                    {log}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Completion Banner */}
        {isCompleted && (
          <div className="mt-4 p-3.5 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-xl flex items-center justify-between text-xs text-emerald-800 dark:text-emerald-300">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>
                Сбор завершен без ошибок. Сформировано объектов в базе: <strong>{collectedCount}</strong>
              </span>
            </div>
            <span className="font-mono text-[11px] text-emerald-600 dark:text-emerald-400">
              Exit code: 0
            </span>
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between text-xs text-neutral-500">
          <span>На сервере логи автоматически пишутся в <code>/logs/*.log</code></span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg transition-colors"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};
