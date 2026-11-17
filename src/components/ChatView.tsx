import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  BookOpen,
  Download,
  FileText,
  Loader2,
  Menu,
  SendHorizontal,
  X,
} from 'lucide-react';
import type { ActiveJobState, ChatMessage, ThemeMode } from '../types/rag';
import { UiIcon } from './UiIcon';

interface ChatViewProps {
  theme: ThemeMode;
  chatTitle: string;
  messages: ChatMessage[];
  activeJob: ActiveJobState | null;
  inspectorOpen: boolean;
  inspectedMsgIndex: number | null;
  onToggleInspector: () => void;
  onInspectMessage: (msgIndex: number) => void;
  onSendMessage: (prompt: string, file: File | null) => Promise<void>;
  onOpenLegalDoc: (parentId: string) => void;
  onOpenPddDoc: (parentId: string) => void;
  onOpenMobileSidebar: () => void;
}

const NEW_GREETING =
  'Здравствуйте. Я юридический ассистент. Готов проанализировать правовые вопросы по аренде с выкупом, лизингу, учёту расходов, налогам (НК РФ), судебной практике ВС РФ и ПДД. Вы можете прикрепить к вопросу документ (PDF, DOCX или TXT).';

const STARTER_QUESTIONS = [
  'Каков порядок расторжения договора аренды транспортного средства с правом выкупа при просрочке платежей по ГК РФ?',
  'Как учитывать лизинговые платежи и транспортный налог при передаче авто в раскат по НК РФ?',
  'Какие документы водитель обязан иметь при себе и предъявлять по ПДД РФ?',
];

const JOB_STATUS_LABELS: Record<string, string> = {
  started: 'Запуск анализа вопроса...',
  retrieving: 'Поиск по кодексам, ВС РФ и ПДД, выделение тем...',
  generating: 'Формирование юридического заключения...',
};

export const ChatView: React.FC<ChatViewProps> = ({
  theme,
  chatTitle,
  messages,
  activeJob,
  inspectorOpen,
  inspectedMsgIndex,
  onToggleInspector,
  onInspectMessage,
  onSendMessage,
  onOpenLegalDoc,
  onOpenPddDoc,
  onOpenMobileSidebar,
}) => {
  const [prompt, setPrompt] = useState('');
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, activeJob?.status]);

  const handleSubmit = async (customPrompt?: string) => {
    const text = (customPrompt ?? prompt).trim();
    if (!text || sending) return;
    setSendError(null);
    setSending(true);
    const fileToSend = attachedFile;
    if (!customPrompt) setPrompt('');
    setAttachedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';

    try {
      await onSendMessage(text, fileToSend);
    } catch (err) {
      setSendError(err instanceof Error ? err.message : 'Ошибка отправки сообщения.');
      if (!customPrompt) setPrompt(text);
    } finally {
      setSending(false);
    }
  };

  const handleMarkdownLinkClick = (
    e: React.MouseEvent<HTMLAnchorElement>,
    href?: string
  ) => {
    if (!href) return;
    if (href.includes('?doc=') || href.includes('#doc-legal_')) {
      e.preventDefault();
      const match =
        href.match(/[?&]doc=([^&#]+)/) || href.match(/#doc-legal_([^&#]+)/);
      if (match?.[1]) {
        onOpenLegalDoc(decodeURIComponent(match[1]));
      }
      return;
    }
    if (href.includes('?pdd=') || href.includes('#doc-pdd_')) {
      e.preventDefault();
      const match =
        href.match(/[?&]pdd=([^&#]+)/) || href.match(/#doc-pdd_([^&#]+)/);
      if (match?.[1]) {
        onOpenPddDoc(decodeURIComponent(match[1]));
      }
    }
  };

  const activeMessageSourcesCount =
    inspectedMsgIndex !== null && messages[inspectedMsgIndex]?.sources
      ? messages[inspectedMsgIndex].sources!.length
      : [...messages].reverse().find((m) => m.role === 'assistant')?.sources?.length || 0;

  return (
    <div className="flex-1 min-w-0 h-full flex flex-col bg-[#F8FAFC] dark:bg-[#0B0F17]">
      {/* Top Bar */}
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
          <h1 className="text-sm lg:text-base font-semibold text-slate-900 dark:text-slate-100 truncate">
            {chatTitle || 'Ассистент (Чат)'}
          </h1>
        </div>

        <button
          type="button"
          onClick={onToggleInspector}
          className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
            inspectorOpen
              ? 'border-[#1E3A8A]/30 dark:border-blue-500/40 bg-blue-50/70 dark:bg-blue-950/40 text-[#1E3A8A] dark:text-blue-300'
              : 'border-[#E2E8F0] dark:border-[#1E293B] bg-white dark:bg-[#111827] text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Источники</span>
          {activeMessageSourcesCount > 0 && (
            <span className="font-mono tabular-nums opacity-80">
              · {activeMessageSourcesCount}
            </span>
          )}
        </button>
      </header>

      {/* Scrollable Chat Messages */}
      <div className="flex-1 overflow-y-auto px-4 lg:px-8 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="space-y-6 pt-4">
              <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl p-6">
                <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">
                  Ассистент
                </div>
                <p className="text-[15px] text-slate-800 dark:text-slate-200 leading-relaxed">
                  {NEW_GREETING}
                </p>
              </div>

              <div>
                <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2.5">
                  Типовые запросы для старта
                </div>
                <div className="grid gap-2">
                  {STARTER_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => handleSubmit(q)}
                      disabled={Boolean(activeJob && activeJob.status !== 'completed' && activeJob.status !== 'error')}
                      className="text-left px-4 py-3 text-sm rounded-xl border border-[#E2E8F0] dark:border-[#1E293B] bg-white dark:bg-[#111827] text-slate-700 dark:text-slate-200 hover:border-blue-400 dark:hover:border-blue-600 hover:bg-slate-50 dark:hover:bg-slate-800/70 transition-colors cursor-pointer"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              const isInspected = inspectedMsgIndex === idx;
              const srcCount = msg.sources?.length || 0;

              if (isUser) {
                return (
                  <div key={msg.id || idx} className="flex justify-end">
                    <div className="max-w-[85%] bg-[#1E3A8A] dark:bg-[#2563EB] text-white rounded-xl px-4 py-3 space-y-2">
                      {msg.attached_filename && (
                        <div className="flex flex-wrap items-center gap-2 text-xs text-blue-100 pb-1.5 border-b border-white/15">
                          <FileText className="w-3.5 h-3.5 shrink-0" />
                          <span className="font-medium">{msg.attached_filename}</span>
                          {msg.attached_chars ? (
                            <span className="font-mono tabular-nums opacity-85">
                              · {msg.attached_chars} зн.
                            </span>
                          ) : null}
                          {msg.attached_download_url && (
                            <a
                              href={msg.attached_download_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 underline hover:text-white"
                            >
                              <Download className="w-3 h-3" />
                              <span>Скачать</span>
                            </a>
                          )}
                        </div>
                      )}
                      <div className="text-[15px] leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <div key={msg.id || idx} className="flex justify-start">
                  <div className="w-full bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl px-5 py-4 space-y-3">
                    {msg.topics && msg.topics.length > 0 && (
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        <span>Темы поиска: </span>
                        <span className="text-slate-700 dark:text-slate-300 font-medium">
                          {msg.topics.join(' · ')}
                        </span>
                      </div>
                    )}

                    {msg.fallback_used && (
                      <div className="px-3 py-2 text-xs rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200">
                        Активирован резервный сценарий из 5 базовых фрагментов
                        {msg.fallback_reason ? ` · ${msg.fallback_reason}` : ''}
                      </div>
                    )}

                    <div className="legal-prose text-[15px] text-slate-800 dark:text-slate-200">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({ href, children }) => (
                            <a
                              href={href}
                              target={href?.startsWith('http') ? '_blank' : undefined}
                              rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
                              onClick={(e) => handleMarkdownLinkClick(e, href)}
                            >
                              {children}
                            </a>
                          ),
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>

                    {srcCount > 0 && (
                      <div className="pt-2.5 border-t border-[#E2E8F0] dark:border-[#1E293B] flex items-center justify-between gap-4 text-xs">
                        <span className="text-slate-500 dark:text-slate-400 font-mono tabular-nums">
                          {msg.fallback_used || srcCount <= 5
                            ? `Первоисточники: ${srcCount} базовых`
                            : `Первоисточники: ${srcCount} (5 базовых + ${srcCount - 5} тематических)`}
                        </span>
                        <button
                          type="button"
                          onClick={() => onInspectMessage(idx)}
                          className={`font-semibold cursor-pointer whitespace-nowrap ${
                            isInspected && inspectorOpen
                              ? 'text-blue-600 dark:text-blue-400'
                              : 'text-[#1E3A8A] hover:text-[#1E40AF] dark:text-blue-400 dark:hover:text-blue-300'
                          }`}
                        >
                          {isInspected && inspectorOpen ? 'Открыто в инспекторе' : 'Открыть в инспекторе'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Active Background Job Progress */}
          {activeJob &&
            activeJob.status !== 'completed' &&
            activeJob.status !== 'error' && (
              <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl px-5 py-4">
                <div className="flex items-center gap-3 text-sm text-slate-800 dark:text-slate-200 font-medium">
                  <Loader2 className="w-4 h-4 animate-spin text-[#1E3A8A] dark:text-blue-400 shrink-0" />
                  <span>{JOB_STATUS_LABELS[activeJob.status] || 'Обработка запроса...'}</span>
                </div>
                <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                  Вы можете переключаться в «Нормативную базу» и «ПДД» — конвейер продолжит работу в фоне.
                </p>
              </div>
            )}

          {activeJob?.status === 'error' && (
            <div className="px-4 py-3 text-xs rounded-xl border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300">
              Ошибка фонового конвейера: {activeJob.error || 'Неизвестная ошибка'}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Bottom Composer */}
      <div className="bg-white dark:bg-[#111827] border-t border-[#E2E8F0] dark:border-[#1E293B] px-4 lg:px-8 py-3 shrink-0">
        <div className="max-w-3xl mx-auto space-y-2">
          {sendError && (
            <div className="px-3 py-2 text-xs rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300">
              {sendError}
            </div>
          )}

          {attachedFile && (
            <div className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg border border-[#E2E8F0] dark:border-[#1E293B] bg-slate-50 dark:bg-[#0B0F17] text-xs">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="w-4 h-4 text-slate-500 shrink-0" />
                <span className="font-medium text-slate-800 dark:text-slate-200 truncate">
                  {attachedFile.name}
                </span>
                <span className="text-slate-500 dark:text-slate-400 font-mono tabular-nums shrink-0">
                  · {(attachedFile.size / 1024).toFixed(1)} КБ
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setAttachedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="p-1 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 cursor-pointer"
                title="Убрать файл"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="flex items-end gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0] || null;
                setAttachedFile(file);
              }}
            />

            <textarea
              rows={1}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void handleSubmit();
                }
              }}
              placeholder="Задайте правовой вопрос по аренде с выкупом, налогам или ПДД..."
              className="flex-1 min-w-0 resize-none px-3.5 py-2.5 text-sm rounded-xl border border-[#CBD5E1] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600/25 focus:border-blue-600 dark:focus:border-blue-500 max-h-40 overflow-y-auto"
            />

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Прикрепить документ (PDF, DOCX, TXT)"
              aria-label="Прикрепить документ"
              className="h-[42px] w-[42px] flex items-center justify-center rounded-xl border border-[#E2E8F0] dark:border-[#1E293B] bg-white dark:bg-[#111827] hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer shrink-0"
            >
              <UiIcon name="add_file" theme={theme} size={18} />
            </button>

            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={!prompt.trim() || sending}
              title="Отправить вопрос"
              aria-label="Отправить вопрос"
              className="h-[42px] px-4 inline-flex items-center justify-center gap-1.5 rounded-xl bg-[#1E3A8A] hover:bg-[#1E40AF] dark:bg-[#2563EB] dark:hover:bg-[#3B82F6] text-white text-sm font-semibold disabled:opacity-50 transition-colors cursor-pointer whitespace-nowrap shrink-0"
            >
              <SendHorizontal className="w-4 h-4" />
              <span className="hidden sm:inline">Отправить</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
