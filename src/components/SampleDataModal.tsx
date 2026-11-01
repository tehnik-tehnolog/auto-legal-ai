import React, { useState } from 'react';
import { X, Copy, Check, FileText, Database } from 'lucide-react';
import { RAGSource } from '../data/ragSources';

interface SampleDataModalProps {
  source: RAGSource | null;
  onClose: () => void;
}

export const SampleDataModal: React.FC<SampleDataModalProps> = ({
  source,
  onClose
}) => {
  const [copied, setCopied] = useState(false);

  if (!source) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(source.sampleContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
            <Database className="w-3.5 h-3.5" />
            <span>Структура данных для RAG</span>
          </div>
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
            {source.name}
          </h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 font-mono">
            {source.sampleFile}
          </p>
        </div>

        {/* Key Fields Checklist */}
        <div className="mt-4 p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 space-y-1">
          <span className="text-xs font-semibold text-neutral-800 dark:text-neutral-200 block">
            Обязательные поля в базе данных:
          </span>
          <div className="flex flex-wrap gap-1.5 text-[11px] font-mono text-neutral-600 dark:text-neutral-300">
            {source.keyFields.map((field, idx) => (
              <span
                key={idx}
                className="bg-white dark:bg-neutral-800 px-2 py-0.5 rounded border border-neutral-200 dark:border-neutral-700"
              >
                {field}
              </span>
            ))}
          </div>
        </div>

        {/* Code Content Area */}
        <div className="mt-4 flex-1 flex flex-col min-h-0 bg-[#0E1117] border border-neutral-800 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 bg-[#161B22] border-b border-neutral-800 text-xs">
            <span className="font-mono text-neutral-400">Пример документа</span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-neutral-300 hover:text-white bg-neutral-800 hover:bg-neutral-700 rounded transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Скопировано!' : 'Копировать'}</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 font-mono text-xs text-neutral-200 leading-relaxed">
            <pre className="whitespace-pre-wrap">{source.sampleContent}</pre>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between text-xs text-neutral-500">
          <span>Регламент обновления: <strong>{source.schedule}</strong></span>
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
