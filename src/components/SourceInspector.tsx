import React, { useState } from 'react';
import { ArrowUpRight, BookOpen, X, AlertTriangle } from 'lucide-react';
import type { ChatMessage, RAGSourceItem, ThemeMode } from '../types/rag';

interface SourceInspectorProps {
  message: ChatMessage | null;
  theme: ThemeMode;
  open: boolean;
  onClose: () => void;
  onOpenLegalDoc: (parentId: string) => void;
  onOpenPddDoc: (parentId: string) => void;
}

const COLLECTION_LABELS: Record<string, string> = {
  legal_laws: 'Нормативно-правовая база',
  court_cases: 'Судебная практика ВС РФ',
  traffic_rules: 'ПДД РФ',
  auto_news: 'Новости авторынка',
};

export const SourceInspector: React.FC<SourceInspectorProps> = ({
  message,
  open,
  onClose,
  onOpenLegalDoc,
  onOpenPddDoc,
}) => {
  const [expandedChunks, setExpandedChunks] = useState<Record<string, boolean>>({});

  if (!open) return null;

  const sources = message?.sources || [];
  const topics = message?.topics || [];
  const fallbackUsed = Boolean(message?.fallback_used);
  const fallbackReason = message?.fallback_reason;

  const toggleExpand = (chunkId: string) => {
    setExpandedChunks((prev) => ({ ...prev, [chunkId]: !prev[chunkId] }));
  };

  const handleOpenSource = (src: RAGSourceItem) => {
    const pId = src.parent_id || '';
    if ((src.collection === 'legal_laws' || src.doc_type === 'legal_law') && pId) {
      onOpenLegalDoc(pId);
      return;
    }
    if ((src.collection === 'traffic_rules' || src.doc_type === 'traffic_rules') && pId) {
      onOpenPddDoc(pId);
      return;
    }
    if (src.url && src.url.startsWith('http')) {
      window.open(src.url, '_blank', 'noopener,noreferrer');
    }
  };

  const panelBody = (
    <aside className="w-full xl:w-[370px] h-full flex flex-col bg-white dark:bg-[#111827] border-l border-[#E2E8F0] dark:border-[#1E293B]">
      <div className="h-14 px-4 flex items-center justify-between border-b border-[#E2E8F0] dark:border-[#1E293B] shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <BookOpen className="w-4 h-4 text-slate-600 dark:text-slate-300 shrink-0" />
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
            Инспектор источников
          </h2>
          {sources.length > 0 && (
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums shrink-0">
              · {sources.length}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          title="Скрыть панель источников"
          className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {!message || sources.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Источники не выбраны
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed max-w-xs mx-auto">
              Задайте вопрос ассистенту или выберите «Источники» под любым ответом в ленте, чтобы увидеть статьи ГК, НК, ПДД.
            </p>
          </div>
        ) : (
          <>
            {/* RAG retrieval mode summary */}
            <div className="pb-4 border-b border-[#E2E8F0] dark:border-[#1E293B] space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-600 dark:text-slate-300">
                  Режим отбора
                </span>
                <span className="font-mono text-slate-900 dark:text-slate-100 tabular-nums">
                  {fallbackUsed || sources.length <= 5
                    ? `${sources.length} базовых`
                    : `${sources.length} (5 + ${sources.length - 5})`}
                </span>
              </div>

              {fallbackUsed && (
                <div className="flex items-start gap-2 p-2.5 rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/30 text-xs text-amber-900 dark:text-amber-200">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
                  <div>
                    <div className="font-medium">Резервный сценарий (5 фрагментов)</div>
                    {fallbackReason && (
                      <div className="mt-0.5 text-[11px] opacity-85 break-words">
                        {fallbackReason}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {topics.length > 0 && (
                <div>
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                    Выделенные темы запроса
                  </div>
                  <div className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed">
                    {topics.map((t, i) => (
                      <React.Fragment key={t}>
                        {i > 0 && (
                          <span className="mx-1.5 text-slate-400" aria-hidden="true">
                            ·
                          </span>
                        )}
                        <span className="font-medium">{t}</span>
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Primary sources list */}
            <div className="divide-y divide-[#E2E8F0] dark:divide-[#1E293B]">
              {sources.map((src, idx) => {
                const isExpanded = Boolean(expandedChunks[src.chunk_id]);
                const excerptLimit = 220;
                const needsTruncate = src.matched_chunk.length > excerptLimit;
                const shownText =
                  isExpanded || !needsTruncate
                    ? src.matched_chunk
                    : `${src.matched_chunk.slice(0, excerptLimit)}...`;

                const canOpenInViewer =
                  Boolean(src.parent_id) &&
                  (src.collection === 'legal_laws' ||
                    src.doc_type === 'legal_law' ||
                    src.collection === 'traffic_rules' ||
                    src.doc_type === 'traffic_rules');
                const hasExternal = Boolean(src.url && src.url.startsWith('http'));

                return (
                  <div key={`${src.chunk_id}_${idx}`} className="py-4 first:pt-0 last:pb-0">
                    <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400 mb-1.5">
                      <div className="flex items-center gap-1.5 min-w-0 truncate">
                        <span className="font-mono font-semibold text-slate-900 dark:text-slate-100 tabular-nums">
                          #{src.citation_id || idx + 1}
                        </span>
                        <span aria-hidden="true">·</span>
                        <span className="truncate">
                          {COLLECTION_LABELS[src.collection] || src.collection}
                        </span>
                        <span aria-hidden="true">·</span>
                        <span className="truncate">
                          {src.source_tag === 'topic_expansion' ? 'По теме' : 'Базовый'}
                        </span>
                      </div>
                      <span className="font-mono font-medium text-slate-700 dark:text-slate-300 tabular-nums shrink-0">
                        {src.similarity_score.toFixed(3)}
                      </span>
                    </div>

                    <h3 className="text-[13px] font-semibold text-slate-900 dark:text-slate-100 leading-snug mb-1">
                      {src.title}
                    </h3>

                    {src.case_number && (
                      <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1.5 tabular-nums">
                        Дело № {src.case_number} {src.date ? `· ${src.date}` : ''}
                      </div>
                    )}

                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                      {shownText}
                    </p>

                    <div className="flex items-center justify-between gap-3 mt-2.5">
                      {needsTruncate ? (
                        <button
                          type="button"
                          onClick={() => toggleExpand(src.chunk_id)}
                          className="text-xs font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 cursor-pointer whitespace-nowrap"
                        >
                          {isExpanded ? 'Свернуть' : 'Полный фрагмент'}
                        </button>
                      ) : (
                        <span />
                      )}

                      {(canOpenInViewer || hasExternal) && (
                        <button
                          type="button"
                          onClick={() => handleOpenSource(src)}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-[#1E3A8A] hover:text-[#1E40AF] dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer whitespace-nowrap shrink-0"
                        >
                          <span>
                            {src.collection === 'traffic_rules' || src.doc_type === 'traffic_rules'
                              ? 'Открыть главу ПДД'
                              : canOpenInViewer
                                ? 'Открыть статью'
                                : 'Первоисточник'}
                          </span>
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </aside>
  );

  return (
    <>
      <div className="hidden xl:block h-full shrink-0">{panelBody}</div>

      <div className="fixed inset-0 z-40 xl:hidden flex justify-end">
        <div className="fixed inset-0 bg-slate-950/40" onClick={onClose} />
        <div className="relative z-10 w-full max-w-sm h-full">{panelBody}</div>
      </div>
    </>
  );
};
