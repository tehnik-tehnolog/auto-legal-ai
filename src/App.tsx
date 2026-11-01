import React, { useState } from 'react';
import { 
  Database, 
  Server, 
  Download, 
  Layers, 
  Clock, 
  CheckCircle2, 
  Sparkles, 
  Play, 
  Code2, 
  BookOpen, 
  Search,
  Filter,
  ArrowUpRight,
  FileText
} from 'lucide-react';
import { Header } from './components/Header';
import { SourceCard } from './components/SourceCard';
import { SampleDataModal } from './components/SampleDataModal';
import { CollectorRunnerModal } from './components/CollectorRunnerModal';
import { CodeViewer } from './components/CodeViewer';
import { ServerDeployGuide } from './components/ServerDeployGuide';
import { RAG_SOURCES, RAGSource } from './data/ragSources';
import { downloadServerScriptsZip } from './utils/zipExport';

export default function App() {
  const [activeTab, setActiveTab] = useState<'sources' | 'scripts' | 'simulator' | 'guide'>('sources');
  const [selectedSourceForSample, setSelectedSourceForSample] = useState<RAGSource | null>(null);
  const [isRunnerOpen, setIsRunnerOpen] = useState<boolean>(false);
  const [runnerInitialCollector, setRunnerInitialCollector] = useState<string>('cars');
  const [activeScriptInViewer, setActiveScriptInViewer] = useState<string>('runner.py');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredSources = RAG_SOURCES.filter(s => 
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.ragPurpose.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.format.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleViewScript = (scriptPath: string) => {
    setActiveScriptInViewer(scriptPath);
    setActiveTab('scripts');
  };

  const handleRunTest = (collectorKey: string) => {
    setRunnerInitialCollector(collectorKey);
    setIsRunnerOpen(true);
  };

  const handleDownloadZip = async () => {
    await downloadServerScriptsZip();
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#0B0F17] text-[#1E293B] dark:text-[#E2E8F0] transition-colors selection:bg-blue-600/20">
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onDownloadZip={handleDownloadZip}
      />

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Tab 1: Источники RAG (Обзор и статус базы) */}
        {activeTab === 'sources' && (
          <div className="space-y-8">
            {/* Hero / Executive Summary */}
            <div className="p-6 sm:p-8 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-2xl shadow-xs space-y-4">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div className="space-y-2 max-w-3xl">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                    <Sparkles className="w-4 h-4" />
                    <span>Шаг 1: Адаптация и запуск скриптов сбора базы данных</span>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
                    RAG-помощник для компании по раскату машин в РФ
                  </h1>
                  <p className="text-xs sm:text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
                    Скрипты из блокнота и файлов реорганизованы в единый серверный комплекс с поддержкой фонового запуска без GUI, автоматической ротацией логов, обходом таймаутов и строгим расписанием обновления через <code>crontab</code>.
                  </p>
                </div>

                <div className="flex flex-wrap lg:flex-col gap-2 shrink-0">
                  <button
                    onClick={() => handleRunTest('cars')}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.98] rounded-xl transition-all shadow-xs"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Протестировать сбор</span>
                  </button>

                  <button
                    onClick={handleDownloadZip}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-xl transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Скачать архив (.zip)</span>
                  </button>
                </div>
              </div>

              {/* KPI Summary strip (tabular numbers) */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-neutral-100 dark:border-neutral-800">
                <div className="space-y-0.5">
                  <span className="text-[11px] text-neutral-500">Всего источников:</span>
                  <div className="text-xl font-bold font-mono tabular-nums text-neutral-900 dark:text-neutral-100">
                    5 разделов
                  </div>
                </div>

                <div className="space-y-0.5">
                  <span className="text-[11px] text-neutral-500">Нормативная база:</span>
                  <div className="text-xl font-bold font-mono tabular-nums text-blue-600 dark:text-blue-400">
                    ~20 000 .md
                  </div>
                </div>

                <div className="space-y-0.5">
                  <span className="text-[11px] text-neutral-500">Судебная практика ВС:</span>
                  <div className="text-xl font-bold font-mono tabular-nums text-neutral-900 dark:text-neutral-100">
                    56 PDF-актов
                  </div>
                </div>

                <div className="space-y-0.5">
                  <span className="text-[11px] text-neutral-500">Готовность к серверу:</span>
                  <div className="text-xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>100% Ready</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Source Cards Matrix */}
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-100">
                    Источники данных для базы знаний
                  </h2>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">
                    Соответствует утвержденной таблице регламентов обновления и структуры документов
                  </p>
                </div>

                {/* Search */}
                <div className="relative w-full sm:w-72">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-neutral-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Поиск по источникам..."
                    className="w-full pl-9 pr-3 py-1.5 text-xs bg-white dark:bg-[#151921] border border-neutral-300 dark:border-neutral-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-600 text-neutral-900 dark:text-neutral-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredSources.map(source => (
                  <SourceCard
                    key={source.id}
                    source={source}
                    onViewSample={setSelectedSourceForSample}
                    onViewScript={handleViewScript}
                    onRunTest={handleRunTest}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Серверные скрипты */}
        {activeTab === 'scripts' && (
          <CodeViewer
            initialScript={activeScriptInViewer}
            onDownloadZip={handleDownloadZip}
          />
        )}

        {/* Tab 3: Тест сбора (Симулятор) */}
        {activeTab === 'simulator' && (
          <div className="space-y-6">
            <div className="p-6 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-2xl space-y-4">
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
                Интерактивное тестирование коллекторов
              </h2>
              <p className="text-xs sm:text-sm text-neutral-600 dark:text-neutral-400 max-w-3xl leading-relaxed">
                Нажмите на любой коллектор ниже, чтобы открыть консоль эмуляции и отследить шаги выполнения: инициализацию браузера в headless-режиме, проверку кодировок, фильтрацию ключевых слов и запись в RAG-структуры.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
                {[
                  { id: 'cars', title: '🚗 raskatof.ru', sub: 'Каталог автомобилей', reg: 'Раз в неделю' },
                  { id: 'news', title: '📰 Автоновости', sub: 'Утильсбор и лизинг', reg: 'Раз в неделю' },
                  { id: 'vsrf', title: '⚖️ ВС РФ', sub: 'Судебные акты в PDF', reg: 'Раз в месяц' },
                  { id: 'laws', title: '📜 ГК / НК РФ', sub: 'Законы с YAML frontmatter', reg: 'Раз в 3 мес' }
                ].map(col => (
                  <button
                    key={col.id}
                    onClick={() => handleRunTest(col.id)}
                    className="p-4 text-left bg-neutral-50 dark:bg-neutral-900 hover:bg-neutral-100 dark:hover:bg-neutral-800/80 border border-neutral-200 dark:border-neutral-800 rounded-xl transition-all space-y-1 group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs sm:text-sm text-neutral-900 dark:text-neutral-100">
                        {col.title}
                      </span>
                      <Play className="w-3.5 h-3.5 text-blue-600 group-hover:scale-110 transition-transform" />
                    </div>
                    <p className="text-[11px] text-neutral-500">
                      {col.sub}
                    </p>
                    <span className="text-[10px] text-blue-600 dark:text-blue-400 font-mono block pt-1">
                      {col.reg}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Инструкция на сервер */}
        {activeTab === 'guide' && (
          <ServerDeployGuide />
        )}
      </main>

      {/* Modal: Sample Data Viewer */}
      <SampleDataModal
        source={selectedSourceForSample}
        onClose={() => setSelectedSourceForSample(null)}
      />

      {/* Modal: Collector Runner Simulator */}
      <CollectorRunnerModal
        isOpen={isRunnerOpen}
        onClose={() => setIsRunnerOpen(false)}
        initialCollector={runnerInitialCollector}
      />
    </div>
  );
}
