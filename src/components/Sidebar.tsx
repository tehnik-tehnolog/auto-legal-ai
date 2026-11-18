import React, { useState } from 'react';
import { Check, LogOut, Moon, Plus, Sun, User as UserIcon, X } from 'lucide-react';
import type { ChatMeta, KBStats, NavSection, ThemeMode, UserProfileMeta } from '../types/rag';
import { UiIcon } from './UiIcon';

interface SidebarProps {
  theme: ThemeMode;
  onToggleTheme: () => void;
  profile: UserProfileMeta;
  activeNav: NavSection;
  onSelectNav: (nav: NavSection) => void;
  onSelectChat: (chatId: string) => void;
  onCreateChat: () => void;
  onTogglePin: (chat: ChatMeta) => void;
  onRenameChat: (chatId: string, newTitle: string) => void;
  onDeleteChat: (chatId: string) => void;
  onLogout: () => void;
  stats: KBStats | null;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  theme,
  onToggleTheme,
  profile,
  activeNav,
  onSelectNav,
  onSelectChat,
  onCreateChat,
  onTogglePin,
  onRenameChat,
  onDeleteChat,
  onLogout,
  stats,
  mobileOpen,
  onCloseMobile,
}) => {
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState('');

  const chats = profile.chats || [];
  const pinnedChats = chats.filter((c) => c.pinned);
  const recentChats = chats.filter((c) => !c.pinned);

  const startRename = (chat: ChatMeta) => {
    setRenamingId(chat.chat_id);
    setRenameDraft(chat.title);
  };

  const commitRename = (chatId: string) => {
    const clean = renameDraft.trim();
    if (clean) {
      onRenameChat(chatId, clean);
    }
    setRenamingId(null);
  };

  const renderChatRow = (chat: ChatMeta) => {
    const isActive = chat.chat_id === profile.active_chat_id && activeNav === 'chat';
    const isRenaming = renamingId === chat.chat_id;

    return (
      <div key={chat.chat_id} className="mb-0.5">
        <div
          className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 transition-colors ${
            isActive
              ? 'bg-slate-200/80 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium'
              : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'
          }`}
        >
          <button
            type="button"
            onClick={() => {
              onSelectChat(chat.chat_id);
              onCloseMobile();
            }}
            className="flex-1 min-w-0 text-left text-[13px] truncate cursor-pointer"
            title={chat.title}
          >
            {chat.title}
          </button>

          <button
            type="button"
            onClick={() => onTogglePin(chat)}
            title={chat.pinned ? 'Открепить чат' : 'Закрепить чат'}
            aria-label={chat.pinned ? 'Открепить чат' : 'Закрепить чат'}
            className="p-1 rounded hover:bg-slate-200/80 dark:hover:bg-slate-700/70 transition-opacity cursor-pointer shrink-0"
          >
            <UiIcon name={chat.pinned ? 'unpin' : 'pin'} theme={theme} size={14} />
          </button>

          <button
            type="button"
            onClick={() => (isRenaming ? setRenamingId(null) : startRename(chat))}
            title="Переименовать чат"
            aria-label="Переименовать чат"
            className="p-1 rounded opacity-0 group-hover:opacity-100 focus:opacity-100 hover:bg-slate-200/80 dark:hover:bg-slate-700/70 transition-opacity cursor-pointer shrink-0"
          >
            <UiIcon name="rename" theme={theme} size={14} />
          </button>

          {chats.length > 1 && (
            <button
              type="button"
              onClick={() => onDeleteChat(chat.chat_id)}
              title="Удалить чат"
              aria-label="Удалить чат"
              className="p-1 rounded opacity-0 group-hover:opacity-100 focus:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/40 transition-opacity cursor-pointer shrink-0"
            >
              <UiIcon name="remove" theme={theme} size={14} />
            </button>
          )}
        </div>

        {isRenaming && (
          <div className="flex items-center gap-1 px-2 pt-1 pb-1.5">
            <input
              type="text"
              autoFocus
              value={renameDraft}
              onChange={(e) => setRenameDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  commitRename(chat.chat_id);
                } else if (e.key === 'Escape') {
                  setRenamingId(null);
                }
              }}
              className="flex-1 min-w-0 px-2 py-1 text-xs rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 focus:outline-none focus:border-blue-600"
            />
            <button
              type="button"
              onClick={() => commitRename(chat.chat_id)}
              title="Сохранить"
              className="p-1 rounded bg-blue-600 text-white hover:bg-blue-700 cursor-pointer shrink-0"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setRenamingId(null)}
              title="Отмена"
              className="p-1 rounded border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer shrink-0"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    );
  };

  const navItems: Array<{ id: NavSection; label: string; icon: 'court' | 'regulatory' | 'pdd' }> = [
    { id: 'chat', label: 'Ассистент (Чат)', icon: 'court' },
    { id: 'legal', label: 'Нормативная база', icon: 'regulatory' },
    { id: 'pdd', label: 'Правила дорожного движения', icon: 'pdd' },
  ];

  const sidebarContent = (
    <aside className="w-[280px] h-full flex flex-col bg-white dark:bg-[#111827] border-r border-[#E2E8F0] dark:border-[#1E293B] select-none">
      {/* Профиль пользователя */}
      <div className="p-4 border-b border-[#E2E8F0] dark:border-[#1E293B]">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-slate-100 dark:bg-slate-800 border border-[#E2E8F0] dark:border-[#1E293B] flex items-center justify-center text-slate-700 dark:text-slate-200 shrink-0">
              <UserIcon className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                {profile.email.endsWith('@guest.local') ? 'Гость' : profile.user_name || 'Юрист'}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
                {profile.email.endsWith('@guest.local') ? 'Гостевой доступ' : profile.email}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={onToggleTheme}
              title={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
              aria-label="Переключить тему"
              className="p-1.5 rounded-lg border border-transparent hover:border-[#E2E8F0] dark:hover:border-[#1E293B] hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <button
              type="button"
              onClick={onLogout}
              title={profile.email.endsWith('@guest.local') ? 'Войти по почте' : 'Выйти из профиля'}
              aria-label={profile.email.endsWith('@guest.local') ? 'Войти по почте' : 'Выйти из профиля'}
              className="p-1.5 rounded-lg border border-transparent hover:border-[#E2E8F0] dark:hover:border-[#1E293B] hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 3 Раздела */}
      <nav className="p-3 space-y-1 border-b border-[#E2E8F0] dark:border-[#1E293B]" aria-label="Разделы">
        {navItems.map((item) => {
          const active = activeNav === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                onSelectNav(item.id);
                onCloseMobile();
              }}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors cursor-pointer whitespace-nowrap ${
                active
                  ? 'bg-[#1E3A8A] dark:bg-[#2563EB] text-white'
                  : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/70'
              }`}
            >
              <UiIcon
                name={item.icon}
                theme={active ? 'dark' : theme}
                size={16}
              />
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Темы чатов */}
      <div className="flex-1 min-h-0 flex flex-col">
        <div className="flex items-center justify-between px-4 pt-3.5 pb-2">
          <h2 className="text-xs font-semibold tracking-wide text-slate-500 dark:text-slate-400">
            Темы чатов
          </h2>
          <button
            type="button"
            onClick={() => {
              onCreateChat();
              onCloseMobile();
            }}
            title="Создать новый чат"
            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md border border-[#E2E8F0] dark:border-[#1E293B] text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer whitespace-nowrap shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Новый</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-3">
          {pinnedChats.length > 0 && (
            <div className="mb-3">
              <div className="px-2 pb-1 text-[11px] font-medium text-slate-400 dark:text-slate-500">
                Закреплённые
              </div>
              {pinnedChats.map(renderChatRow)}
            </div>
          )}

          {recentChats.length > 0 && (
            <div>
              {pinnedChats.length > 0 && (
                <div className="px-2 pb-1 text-[11px] font-medium text-slate-400 dark:text-slate-500">
                  Недавние
                </div>
              )}
              {recentChats.slice(0, 20).map(renderChatRow)}
            </div>
          )}
        </div>
      </div>

      {/* Спокойный статистический футер базы знаний без пилюль */}
      <div className="px-4 py-3 border-t border-[#E2E8F0] dark:border-[#1E293B] text-[11px] text-slate-500 dark:text-slate-400 tabular-nums">
        {stats ? (
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 leading-relaxed">
            <span>{stats.legal} статей</span>
            <span aria-hidden="true">·</span>
            <span>ГК {stats.civics}</span>
            <span aria-hidden="true">·</span>
            <span>НК {stats.tax}</span>
            <span aria-hidden="true">·</span>
            <span>ПДД {stats.pdd} глав</span>
          </div>
        ) : (
          <span>Загрузка статистики базы...</span>
        )}
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:block h-full shrink-0">{sidebarContent}</div>

      {/* Mobile slide-over */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-950/50 transition-opacity"
            onClick={onCloseMobile}
          />
          <div className="relative z-10 h-full">{sidebarContent}</div>
        </div>
      )}
    </>
  );
};
