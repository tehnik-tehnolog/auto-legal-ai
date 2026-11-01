import React from 'react';
import { 
  FileText, 
  Clock, 
  Calendar, 
  Layers, 
  Play, 
  Code2, 
  ExternalLink,
  CheckCircle2,
  Database
} from 'lucide-react';
import { RAGSource } from '../data/ragSources';

interface SourceCardProps {
  source: RAGSource;
  onViewSample: (source: RAGSource) => void;
  onViewScript: (scriptPath: string) => void;
  onRunTest: (collectorKey: string) => void;
}

export const SourceCard: React.FC<SourceCardProps> = ({
  source,
  onViewSample,
  onViewScript,
  onRunTest
}) => {
  const getCollectorArg = (id: string) => {
    switch (id) {
      case 'gk':
      case 'nk':
        return 'laws';
      case 'vsrf':
        return 'vsrf';
      case 'cars':
        return 'cars';
      case 'news':
        return 'news';
      default:
        return 'all';
    }
  };

  return (
    <div className="p-5 sm:p-6 bg-white dark:bg-[#151921] border border-neutral-200 dark:border-neutral-800 rounded-xl space-y-4 hover:border-neutral-300 dark:hover:border-neutral-700 transition-colors shadow-xs">
      {/* Top Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="w-7 h-7 rounded-lg bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 font-bold text-xs flex items-center justify-center font-mono">
            #{source.number}
          </span>
          <div>
            <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-100">
              {source.name}
            </h3>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {source.section}
            </p>
          </div>
        </div>

        {/* Clean unboxed metadata separator */}
        <div className="flex items-center gap-1.5 text-xs text-neutral-500 dark:text-neutral-400 shrink-0 font-mono">
          <Clock className="w-3.5 h-3.5 text-blue-500" />
          <span>{source.schedule}</span>
        </div>
      </div>

      {/* Purpose in RAG */}
      <div className="p-3 bg-neutral-50 dark:bg-neutral-900/70 rounded-lg text-xs leading-relaxed text-neutral-700 dark:text-neutral-300 border border-neutral-100 dark:border-neutral-800/80">
        <span className="font-semibold text-neutral-900 dark:text-neutral-100 block mb-0.5">
          Назначение в RAG компании:
        </span>
        {source.ragPurpose}
      </div>

      {/* Data details strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-2 text-neutral-600 dark:text-neutral-400">
          <Database className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
          <span>Объем:</span>
          <strong className="text-neutral-900 dark:text-neutral-100 font-medium truncate">
            {source.volume}
          </strong>
        </div>

        <div className="flex items-center gap-2 text-neutral-600 dark:text-neutral-400">
          <FileText className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
          <span>Формат:</span>
          <strong className="text-neutral-900 dark:text-neutral-100 font-medium truncate font-mono text-[11px]">
            {source.format}
          </strong>
        </div>
      </div>

      {/* Cron rule */}
      <div className="flex items-center justify-between text-[11px] pt-1 border-t border-neutral-100 dark:border-neutral-800 text-neutral-500">
        <span>Cron на сервере:</span>
        <code className="font-mono text-blue-600 dark:text-blue-400 bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 rounded">
          {source.scheduleCron}
        </code>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <button
          onClick={() => onViewSample(source)}
          className="flex-1 min-w-[130px] flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg transition-colors"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Пример данных</span>
        </button>

        <button
          onClick={() => onViewScript(source.collectorFile)}
          className="flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40 rounded-lg border border-blue-200 dark:border-blue-800 transition-colors"
        >
          <Code2 className="w-3.5 h-3.5" />
          <span>Код скрипта</span>
        </button>

        <button
          onClick={() => onRunTest(getCollectorArg(source.id))}
          className="flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-xs"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Тест</span>
        </button>
      </div>
    </div>
  );
};
