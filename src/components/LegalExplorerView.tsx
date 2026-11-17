import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowLeft, ArrowUpRight, Menu, Search } from 'lucide-react';
import type { LegalChapterDoc, LegalSummaryItem, ThemeMode } from '../types/rag';
import { apiFetch } from '../utils/api';
import { UiIcon } from './UiIcon';

interface LegalExplorerViewProps {
  theme: ThemeMode;
  activeDocId: string | null;
  onSelectDoc: (docId: string | null) => void;
  onOpenMobileSidebar: () => void;
}

export const LegalExplorerView: React.FC<LegalExplorerViewProps> = ({
  theme,
  activeDocId,
  onSelectDoc,
  onOpenMobileSidebar,
}) => {
  const [codes, setCodes] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCode, setSelectedCode] = useState('Все акты');
  const [selectedCategory, setSelectedCategory] = useState('Все категории');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  const [items, setItems] = useState<LegalSummaryItem[]>([]);
  const [totalFiltered, setTotalFiltered] = useState(0);
  const [truncated, setTruncated] = useState(false);
  const [singleDoc, setSingleDoc] = useState<LegalChapterDoc | null>(null);
  const [openedDoc, setOpenedDoc] = useState<LegalChapterDoc | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(searchQuery), 220);
    return () => window.clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        if (activeDocId) {
          const res = await apiFetch<{
            doc: LegalChapterDoc | null;
            codes: string[];
            categories: string[];
          }>(`/api/kb/legal?docId=${encodeURIComponent(activeDocId)}`);
          if (!cancelled) {
            setOpenedDoc(res.doc);
            if (res.codes?.length) setCodes(res.codes);
            if (res.categories?.length) setCategories(res.categories);
          }
        } else {
          setOpenedDoc(null);
          const params = new URLSearchParams({
            code: selectedCode,
            category: selectedCategory,
            q: debouncedQuery,
          });
          const res = await apiFetch<{
            items: LegalSummaryItem[];
            singleDoc: LegalChapterDoc | null;
            totalFiltered: number;
            truncated?: boolean;
            codes: string[];
            categories: string[];
          }>(`/api/kb/legal?${params.toString()}`);
          if (!cancelled) {
            setItems(res.items || []);
            setSingleDoc(res.singleDoc || null);
            setTotalFiltered(res.totalFiltered || 0);
            setTruncated(Boolean(res.truncated));
            if (res.codes?.length) setCodes(res.codes);
            if (res.categories?.length) setCategories(res.categories);
          }
        }
      } catch {
        // ignore transient errors
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [activeDocId, selectedCode, selectedCategory, debouncedQuery]);

  const displayedDoc = activeDocId ? openedDoc : singleDoc;

  const renderArticle = (doc: LegalChapterDoc, showBack: boolean) => (
    <div className="space-y-4">
      {showBack && (
        <button
          type="button"
          onClick={() => onSelectDoc(null)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-[#E2E8F0] dark:border-[#1E293B] bg-white dark:bg-[#111827] text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Вернуться к списку выборки</span>
        </button>
      )}

      <article className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl p-6 lg:p-8 space-y-5">
        <header className="space-y-2 pb-5 border-b border-[#E2E8F0] dark:border-[#1E293B]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              <span>{doc.code || doc.section || 'ГК РФ'}</span>
              {doc.chapter_number && (
                <>
                  <span className="mx-1.5" aria-hidden="true">·</span>
                  <span>{doc.chapter_number}</span>
                </>
              )}
              {doc.category && (
                <>
                  <span className="mx-1.5" aria-hidden="true">·</span>
                  <span>{doc.category}</span>
                </>
              )}
            </div>

            {doc.original_url && (
              <a
                href={doc.original_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-semibold text-[#1E3A8A] hover:text-[#1E40AF] dark:text-blue-400 dark:hover:text-blue-300 whitespace-nowrap"
              >
                <span>Первоисточник (docs.cntd.ru)</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </a>
            )}
          </div>

          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 leading-snug">
            {doc.title}
          </h2>
        </header>

        <div className="legal-prose max-w-none text-[15px] text-slate-800 dark:text-slate-200">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {doc.body || doc.full_text || ''}
          </ReactMarkdown>
        </div>

        {doc.details && (
          <footer className="pt-4 border-t border-[#E2E8F0] dark:border-[#1E293B] text-xs text-slate-500 dark:text-slate-400">
            Реквизиты: {doc.details}
          </footer>
        )}
      </article>
    </div>
  );

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
          <UiIcon name="regulatory" theme={theme} size={18} />
          <h1 className="text-sm lg:text-base font-semibold text-slate-900 dark:text-slate-100 truncate">
            Нормативно-правовая база
          </h1>
        </div>
        <span className="text-xs font-mono text-slate-500 dark:text-slate-400 tabular-nums shrink-0">
          ГК · НК · КоАП · Лизинг
        </span>
      </header>

      <div className="flex-1 overflow-y-auto px-4 lg:px-8 py-6">
        <div className="max-w-5xl mx-auto space-y-5">
          {/* Фильтры */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl p-4">
            <div className="md:col-span-3">
              <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                Кодекс / Закон
              </label>
              <select
                value={selectedCode}
                onChange={(e) => {
                  onSelectDoc(null);
                  setSelectedCode(e.target.value);
                }}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 focus:outline-none focus:border-blue-600"
              >
                <option value="Все акты">Все акты</option>
                {codes.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-4">
              <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                Категория (тема)
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => {
                  onSelectDoc(null);
                  setSelectedCategory(e.target.value);
                }}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#CBD5E1] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 focus:outline-none focus:border-blue-600"
              >
                <option value="Все категории">Все категории</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-5">
              <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                Поиск по статье, главе или термину
              </label>
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    onSelectDoc(null);
                    setSearchQuery(e.target.value);
                  }}
                  placeholder="Например: 615, лизинг, выкуп, налог..."
                  className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-[#CBD5E1] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-600"
                />
              </div>
            </div>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((n) => (
                <div
                  key={n}
                  className="h-16 rounded-xl border border-[#E2E8F0] dark:border-[#1E293B] bg-white dark:bg-[#111827] animate-pulse"
                />
              ))}
            </div>
          ) : displayedDoc ? (
            renderArticle(displayedDoc, Boolean(activeDocId))
          ) : items.length > 0 ? (
            <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl overflow-hidden">
              <div className="px-4 py-2.5 border-b border-[#E2E8F0] dark:border-[#1E293B] flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <span>
                  Найдено статей:{' '}
                  <strong className="font-mono text-slate-900 dark:text-slate-100 tabular-nums">
                    {totalFiltered}
                  </strong>
                  {truncated && ' (показаны первые 300 — уточните фильтр)'}
                </span>
              </div>

              <div className="divide-y divide-[#E2E8F0] dark:divide-[#1E293B]">
                {items.map((doc) => (
                  <div
                    key={doc.parent_id}
                    className="px-4 py-3 flex items-center justify-between gap-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <div className="min-w-0 space-y-0.5">
                      <div className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                        {doc.title}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
                        <span>{doc.code}</span>
                        {doc.chapter_number && (
                          <>
                            <span className="mx-1.5" aria-hidden="true">·</span>
                            <span>{doc.chapter_number}</span>
                          </>
                        )}
                        {doc.category && (
                          <>
                            <span className="mx-1.5" aria-hidden="true">·</span>
                            <span>{doc.category}</span>
                          </>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => onSelectDoc(doc.parent_id)}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg border border-[#E2E8F0] dark:border-[#1E293B] bg-white dark:bg-[#0B0F17] text-slate-800 dark:text-slate-200 hover:border-blue-500 hover:text-[#1E3A8A] dark:hover:text-blue-400 transition-colors cursor-pointer whitespace-nowrap shrink-0"
                    >
                      Читать
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl p-10 text-center text-sm text-slate-500 dark:text-slate-400">
              По заданным фильтрам статей не найдено. Попробуйте изменить запрос.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
