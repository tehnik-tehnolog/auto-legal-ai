import React, { useState } from 'react';
import { ArrowRight, Moon, Sun, User as UserIcon } from 'lucide-react';
import type { ChatMessage, ThemeMode, UserProfileMeta } from '../types/rag';
import { apiFetch, setStoredDeviceToken } from '../utils/api';
import { UiIcon } from './UiIcon';

interface AuthGateProps {
  theme: ThemeMode;
  onToggleTheme: () => void;
  onAuthenticated: (profile: UserProfileMeta, messages: ChatMessage[]) => void;
}

export const AuthGate: React.FC<AuthGateProps> = ({
  theme,
  onToggleTheme,
  onAuthenticated,
}) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [guestSubmitting, setGuestSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const cleanName = name.trim();
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanName) {
      setError('Пожалуйста, введите ваше имя.');
      return;
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(cleanEmail)) {
      setError('Введите корректный адрес электронной почты (например: lawyer@company.ru).');
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiFetch<{
        authenticated: boolean;
        profile: UserProfileMeta;
        messages: ChatMessage[];
        deviceToken: string;
      }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ name: cleanName, email: cleanEmail }),
      });

      setStoredDeviceToken(res.deviceToken);
      onAuthenticated(res.profile, res.messages || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка входа. Попробуйте ещё раз.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGuestLogin = async () => {
    setError(null);
    setGuestSubmitting(true);
    try {
      const res = await apiFetch<{
        authenticated: boolean;
        profile: UserProfileMeta;
        messages: ChatMessage[];
        deviceToken: string;
      }>('/api/auth/guest', {
        method: 'POST',
        body: JSON.stringify({}),
      });

      setStoredDeviceToken(res.deviceToken);
      onAuthenticated(res.profile, res.messages || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка гостевого входа. Попробуйте ещё раз.');
    } finally {
      setGuestSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F8FAFC] dark:bg-[#0B0F17] text-[#0F172A] dark:text-[#F1F5F9] transition-colors">
      <div className="flex items-center justify-end px-6 py-4">
        <button
          type="button"
          onClick={onToggleTheme}
          className="inline-flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-lg border border-[#E2E8F0] dark:border-[#1E293B] bg-white dark:bg-[#111827] text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/70 transition-colors cursor-pointer"
          aria-label="Переключить тему"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          <span>{theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}</span>
        </button>
      </div>

      <main className="flex-1 flex items-center justify-center px-4 pb-16">
        <div className="w-full max-w-md bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#1E293B] rounded-xl p-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800/80 border border-[#E2E8F0] dark:border-[#1E293B] flex items-center justify-center">
              <UiIcon name="court" theme={theme} size={22} alt="Юридический ассистент" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                Юридический RAG-ассистент
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Правовая база РФ · ГК · НК · КоАП · ВС РФ · ПДД
              </p>
            </div>
          </div>

          <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-6">
            Представьтесь один раз — браузер запомнит это устройство и откроет ваши диалоги автоматически при следующем визите.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label
                htmlFor="auth-name"
                className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Имя и фамилия
              </label>
              <input
                id="auth-name"
                type="text"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Алексей Соколов"
                className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#CBD5E1] dark:border-[#334155] bg-white dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 dark:focus:border-blue-500 transition-colors"
              />
            </div>

            <div>
              <label
                htmlFor="auth-email"
                className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5"
              >
                Корпоративная почта
              </label>
              <input
                id="auth-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="lawyer@company.ru"
                className="w-full px-3.5 py-2.5 text-sm rounded-lg border border-[#CBD5E1] dark:border-[#334155] bg-white dark:bg-[#0B0F17] text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 dark:focus:border-blue-500 transition-colors"
              />
            </div>

            {error && (
              <div
                role="alert"
                className="px-3.5 py-2.5 text-xs font-medium rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || guestSubmitting}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg bg-[#1E3A8A] hover:bg-[#1E40AF] dark:bg-[#2563EB] dark:hover:bg-[#3B82F6] text-white disabled:opacity-60 transition-colors cursor-pointer whitespace-nowrap"
            >
              <span>{submitting ? 'Вход в рабочее пространство...' : 'Войти и запомнить устройство'}</span>
              {!submitting && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>

          <div className="relative my-5 flex items-center">
            <div className="flex-1 border-t border-[#E2E8F0] dark:border-[#1E293B]" />
            <span className="px-3 text-xs text-slate-400 dark:text-slate-500">или</span>
            <div className="flex-1 border-t border-[#E2E8F0] dark:border-[#1E293B]" />
          </div>

          <button
            type="button"
            disabled={submitting || guestSubmitting}
            onClick={() => void handleGuestLogin()}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg border border-[#CBD5E1] dark:border-[#334155] bg-[#F8FAFC] dark:bg-[#0B0F17] text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/80 disabled:opacity-60 transition-colors cursor-pointer whitespace-nowrap"
          >
            <UserIcon className="w-4 h-4" />
            <span>{guestSubmitting ? 'Создание гостевой сессии...' : 'Войти как гость'}</span>
          </button>
        </div>
      </main>
    </div>
  );
};
