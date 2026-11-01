import React from 'react';
import { Download, Server, Play, Code2, BookOpen, Database } from 'lucide-react';

interface HeaderProps {
  activeTab: 'sources' | 'scripts' | 'simulator' | 'guide';
  setActiveTab: (tab: 'sources' | 'scripts' | 'simulator' | 'guide') => void;
  onDownloadZip: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onDownloadZip
}) => {
  return (
    <header className="sticky top-0 z-40 border-b transition-colors bg-white/95 dark:bg-[#0E1117]/95 backdrop-blur-md border-neutral-200 dark:border-neutral-800">
      <div className="flex items-center justify-between px-4 sm:px-6 py-3 max-w-7xl mx-auto gap-4">
        {/* Zone 1: Single Text Element Wordmark */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-xs">
            <Database className="w-4 h-4" />
          </div>
          <a
            href="/"
            className="text-base sm:text-lg font-bold tracking-tight text-neutral-900 dark:text-neutral-100 whitespace-nowrap shrink-0"
          >
            RAG Auto Collector
          </a>
        </div>

        {/* Zone 2: Navigation Links (single-line, concise) */}
        <nav className="hidden md:flex items-center gap-6 text-xs sm:text-sm font-medium text-neutral-600 dark:text-neutral-400">
          <button
            onClick={() => setActiveTab('sources')}
            className={`transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'sources'
                ? 'text-blue-600 dark:text-blue-400 font-semibold underline underline-offset-4'
                : 'hover:text-neutral-900 dark:hover:text-neutral-100'
            }`}
          >
            Источники RAG
          </button>
          <button
            onClick={() => setActiveTab('scripts')}
            className={`transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'scripts'
                ? 'text-blue-600 dark:text-blue-400 font-semibold underline underline-offset-4'
                : 'hover:text-neutral-900 dark:hover:text-neutral-100'
            }`}
          >
            Серверные скрипты
          </button>
          <button
            onClick={() => setActiveTab('simulator')}
            className={`transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'simulator'
                ? 'text-blue-600 dark:text-blue-400 font-semibold underline underline-offset-4'
                : 'hover:text-neutral-900 dark:hover:text-neutral-100'
            }`}
          >
            Тест сбора
          </button>
          <button
            onClick={() => setActiveTab('guide')}
            className={`transition-colors whitespace-nowrap shrink-0 ${
              activeTab === 'guide'
                ? 'text-blue-600 dark:text-blue-400 font-semibold underline underline-offset-4'
                : 'hover:text-neutral-900 dark:hover:text-neutral-100'
            }`}
          >
            Инструкция на сервер
          </button>
        </nav>

        {/* Zone 3: 1 Primary Action */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onDownloadZip}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:scale-[0.98] rounded-lg shadow-xs transition-all whitespace-nowrap shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Скачать архив (.zip)</span>
          </button>
        </div>
      </div>
    </header>
  );
};
