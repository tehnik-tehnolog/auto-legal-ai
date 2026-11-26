import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Menu, Search } from 'lucide-react';
import type { PddChapterDoc, PddTocItem, ThemeMode } from '../types/rag';
import { apiFetch } from '../utils/api';
import { UiIcon } from './UiIcon';

interface PddExplorerViewProps {
  theme: ThemeMode;
  activePddId: string | null;
  onSelectPdd: (pddId: string) => void;
  onOpenMobileSidebar: () => void;
}

function formatPddLabel(c: { chapter_number?: string; chapter_title?: string; title?: string }): string {
  const num = (c.chapter_number || '').trim();
  const rawTitle = (c.chapter_title || c.title || '').trim();
  const cleanTitle = rawTitle.replace(/^(?:ПДД РФ:\s*)?\d+(?:\.\d+)*\.?\s*/i, '');
  return `${num} ${cleanTitle}`.trim();
}

export const PddExplorerView: React.FC<PddExplorerViewProps> = ({
  theme,
  activePddId,
  onSelectPdd,
  onOpenMobileSidebar,
}) => {
  const [toc, setToc] = useState<PddTocItem[]>([]);
  const [chapter, setChapter] = useState<PddChapterDoc | null>(null);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const qs = activePddId ? `?pddId=${encodeURIComponent(activePddId)}` : '';
        const res = await apiFetch<{
          toc: PddTocItem[];
          activeChapter: PddChapterDoc | null;
        }>(`/api/kb/pdd${qs}`);
        if (!cancelled) {
          setToc(res.toc || []);
          setChapter(res.activeChapter || null);
        }
      } catch {
        // ignore transient error
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [activePddId]);

  const rawBody = chapter ? chapter.body || chapter.full_text || '' : '';
  const displayedBody = (() => {
    const q = keyword.trim().toLowerCase();
    if (!q) return rawBody;
    return rawBody
      .split('\n')
      .map((line) => (line.toLowerCase().includes(q) && line.trim() ? `**${line.trim()}**` : line))
      .join('\n');
  })();

  return (
    <div className="flex-1 min-w-0 h-full flex flex-col bg-[#F8FAFC] dark:bg-[#0B0F17]">
      <header className="h-14 px-4 lg:px-6 flex items-center justify-between gap-4 bg-white dark:bg-[#111827] border-b border-[#E2E8F0] dark:border-[#1E293B] shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={onOpenMobileSidebar}
            className="lg:hidden p-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
            aria-label="Открыть меню"
          >
            <Menu className="w-5 h-5" />
          </button>
          <UiIcon name="pdd" theme={theme} size={18} />
          <h1 className="text-sm lg:text-base font-semibold text-slate-900 dark:text-slate-100 truncate">
            Правила дорожного движения РФ
          </h1>
        </div>
        <span className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums shrink-0">
          {toc.length} разделов
        </span>
      </header>

      <div className="flex-1 overflow-y-auto px-4 lg:px-8 py-6">
        <div className="max-w-5xl mx-auto space-y-5">
          {/* Chapter selector and text filter */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl p-4">
            <div className="md:col-span-7">
              <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                Глава или раздел ПДД РФ
              </label>
              <select
                value={activePddId || chapter?.parent_id || ''}
                onChange={(e) => onSelectPdd(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 focus:outline-none focus:border-blue-600"
              >
                {toc.map((c) => (
                  <option key={c.parent_id} value={c.parent_id}>
                    {formatPddLabel(c)}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-5">
              <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                Подсветка по тексту выбранной главы
              </label>
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="Например: скорость, обгон, тормоз..."
                  className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-[#CBD5E1] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-600"
                />
              </div>
            </div>
          </div>

          {loading && !chapter ? (
            <div className="h-64 rounded-xl border border-[#E2E8F0] dark:border-[#1E293B] bg-white dark:bg-[#111827] animate-pulse" />
          ) : chapter ? (
            <article
              className={`bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl p-6 lg:p-8 space-y-5 transition-opacity ${
                loading ? 'opacity-60' : 'opacity-100'
              }`}
            >
              <header className="space-y-1.5 pb-4 border-b border-[#E2E8F0] dark:border-[#1E293B]">
                <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                  {chapter.chapter_number} · {chapter.parent_id}
                </div>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                  {chapter.title}
                </h2>
              </header>

              <div className="legal-prose max-w-none text-[15px] text-slate-800 dark:text-slate-200">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{displayedBody}</ReactMarkdown>
              </div>
            </article>
          ) : (
            <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl p-10 text-center text-sm text-slate-500 dark:text-slate-400">
              Разделы ПДД не найдены. Проверьте наличие `data/pdd/pdd_chapters.jsonl`.
            </div>
          )}

          {/* Table of contents */}
          {toc.length > 0 && (
            <details className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl">
              <summary className="px-5 py-3.5 text-sm font-semibold text-slate-900 dark:text-slate-100 cursor-pointer">
                Полное оглавление Правил дорожного движения ({toc.length})
              </summary>
              <div className="divide-y divide-[#E2E8F0] dark:divide-[#1E293B] border-t border-[#E2E8F0] dark:border-[#1E293B]">
                {toc.map((ch) => {
                  const isCurrent = ch.parent_id === (activePddId || chapter?.parent_id);
                  return (
                    <div
                      key={ch.parent_id}
                      className={`px-5 py-2.5 flex items-center justify-between gap-4 ${
                        isCurrent
                          ? 'bg-slate-100 dark:bg-slate-800/80'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                      }`}
                    >
                      <span
                        className={`text-xs ${
                          isCurrent
                            ? 'font-semibold text-[#1E3A8A] dark:text-blue-400'
                            : 'font-medium text-slate-800 dark:text-slate-200'
                        }`}
                      >
                        {formatPddLabel(ch)}
                      </span>
                      <button
                        type="button"
                        onClick={() => onSelectPdd(ch.parent_id)}
                        className="text-xs font-semibold text-[#1E3A8A] hover:text-[#1E40AF] dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer whitespace-nowrap"
                      >
                        {isCurrent ? 'Открыто' : 'Перейти'}
                      </button>
                    </div>
                  );
                })}
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
};
