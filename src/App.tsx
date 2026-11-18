import React, { useEffect, useState } from 'react';
import { AuthGate } from './components/AuthGate';
import { ChatView } from './components/ChatView';
import { LegalExplorerView } from './components/LegalExplorerView';
import { PddExplorerView } from './components/PddExplorerView';
import { Sidebar } from './components/Sidebar';
import { SourceInspector } from './components/SourceInspector';
import type {
  ActiveJobState,
  ChatMessage,
  ChatMeta,
  KBStats,
  NavSection,
  ThemeMode,
  UserProfileMeta,
} from './types/rag';
import {
  apiFetch,
  getStoredDeviceToken,
  getStoredTheme,
  saveStoredTheme,
  setStoredDeviceToken,
} from './utils/api';

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => getStoredTheme());
  const [checkingSession, setCheckingSession] = useState(true);
  const [profile, setProfile] = useState<UserProfileMeta | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stats, setStats] = useState<KBStats | null>(null);

  const [activeNav, setActiveNav] = useState<NavSection>('chat');
  const [activeLegalDocId, setActiveLegalDocId] = useState<string | null>(null);
  const [activePddId, setActivePddId] = useState<string | null>(null);

  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [inspectedMsgIndex, setInspectedMsgIndex] = useState<number | null>(null);
  const [activeJob, setActiveJob] = useState<ActiveJobState | null>(null);

  // Sync Tailwind dark class on <html>
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    saveStoredTheme(theme);
  }, [theme]);

  // Read deep links (?doc=... / ?pdd=...)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const docParam = params.get('doc');
    const pddParam = params.get('pdd');
    if (docParam) {
      setActiveLegalDocId(docParam.replace(/^(?:#?doc-legal_|#?legal_|#)/, ''));
      setActiveNav('legal');
    } else if (pddParam) {
      setActivePddId(pddParam.replace(/^(?:#?doc-pdd_|#)/, ''));
      setActiveNav('pdd');
    }
  }, []);

  // Silent device auto-login on mount + KB stats
  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      const token = getStoredDeviceToken();
      try {
        if (token) {
          const res = await apiFetch<{
            authenticated: boolean;
            profile?: UserProfileMeta;
            messages?: ChatMessage[];
          }>('/api/auth/session', { method: 'POST', body: JSON.stringify({ deviceToken: token }) });
          if (!cancelled && res.authenticated && res.profile) {
            setProfile(res.profile);
            setMessages(res.messages || []);
          } else if (!cancelled && !res.authenticated) {
            setStoredDeviceToken('');
          }
        }
      } catch {
        // show auth screen gracefully
      } finally {
        if (!cancelled) setCheckingSession(false);
      }
    }
    void bootstrap();

    apiFetch<KBStats>('/api/kb/stats')
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  // Keep Render warm when tab regains visibility
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetch('/api/health', { cache: 'no-store' }).catch(() => {});
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

  // Global background polling for active RAG job (continues even when user switches tabs!)
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'error') {
      return;
    }

    let cancelled = false;
    const poll = async () => {
      try {
        const res = await apiFetch<{
          jobId: string;
          chatId: string;
          status: ActiveJobState['status'];
          result?: {
            assistantMessage: ChatMessage;
          } | null;
          renamedTitle?: string | null;
          error?: string | null;
        }>(`/api/chat/jobs/${encodeURIComponent(activeJob.jobId)}`);

        if (cancelled) return;

        if (res.status === 'completed' && res.result?.assistantMessage) {
          setActiveJob({ jobId: res.jobId, chatId: res.chatId, status: 'completed' });
          setProfile((prev) => {
            if (!prev) return prev;
            const updatedChats = res.renamedTitle
              ? prev.chats.map((c) =>
                  c.chat_id === res.chatId ? { ...c, title: res.renamedTitle! } : c
                )
              : prev.chats;
            return { ...prev, chats: updatedChats };
          });
          setMessages((prev) => {
            // Only append to live view if this chat is currently visible
            if (profile?.active_chat_id !== res.chatId) return prev;
            const next = [...prev, res.result!.assistantMessage];
            setInspectedMsgIndex(next.length - 1);
            return next;
          });
        } else if (res.status === 'error') {
          setActiveJob({
            jobId: res.jobId,
            chatId: res.chatId,
            status: 'error',
            error: res.error,
          });
        } else if (res.status !== activeJob.status) {
          setActiveJob({ jobId: res.jobId, chatId: res.chatId, status: res.status });
        }
      } catch {
        // retry on next tick
      }
    };

    const interval = window.setInterval(() => {
      void poll();
    }, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [activeJob, profile?.active_chat_id]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleLogout = async () => {
    const token = getStoredDeviceToken();
    setStoredDeviceToken('');
    setProfile(null);
    setMessages([]);
    setActiveJob(null);
    setInspectedMsgIndex(null);
    if (token) {
      apiFetch('/api/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ deviceToken: token }),
      }).catch(() => {});
    }
  };

  const handleSelectChat = async (chatId: string) => {
    setActiveNav('chat');
    setInspectedMsgIndex(null);
    const res = await apiFetch<{ profile: UserProfileMeta; messages: ChatMessage[] }>(
      `/api/chats/${encodeURIComponent(chatId)}/activate`,
      { method: 'POST' }
    );
    setProfile(res.profile);
    setMessages(res.messages || []);
  };

  const handleCreateChat = async () => {
    setActiveNav('chat');
    setInspectedMsgIndex(null);
    const res = await apiFetch<{ profile: UserProfileMeta; messages: ChatMessage[] }>(
      '/api/chats',
      { method: 'POST', body: JSON.stringify({}) }
    );
    setProfile(res.profile);
    setMessages(res.messages || []);
  };

  const handleTogglePin = async (chat: ChatMeta) => {
    const res = await apiFetch<{ profile: UserProfileMeta }>(
      `/api/chats/${encodeURIComponent(chat.chat_id)}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ pinned: !chat.pinned }),
      }
    );
    setProfile(res.profile);
  };

  const handleRenameChat = async (chatId: string, newTitle: string) => {
    const res = await apiFetch<{ profile: UserProfileMeta }>(
      `/api/chats/${encodeURIComponent(chatId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ title: newTitle }),
      }
    );
    setProfile(res.profile);
  };

  const handleDeleteChat = async (chatId: string) => {
    const res = await apiFetch<{ profile: UserProfileMeta; messages: ChatMessage[] }>(
      `/api/chats/${encodeURIComponent(chatId)}`,
      { method: 'DELETE' }
    );
    setProfile(res.profile);
    setMessages(res.messages || []);
    setInspectedMsgIndex(null);
  };

  const handleSendMessage = async (prompt: string, file: File | null) => {
    if (!profile?.active_chat_id) return;
    const chatId = profile.active_chat_id;

    const form = new FormData();
    form.append('prompt', prompt);
    form.append('chatId', chatId);
    if (file) {
      form.append('file', file);
      form.append('originalFilename', file.name);
    }

    const res = await apiFetch<{ jobId: string; userMessage: ChatMessage }>('/api/chat/ask', {
      method: 'POST',
      body: form,
    });

    setMessages((prev) => [...prev, res.userMessage]);
    setActiveJob({ jobId: res.jobId, chatId, status: 'started' });
  };

  const openLegalDoc = (docId: string | null) => {
    setActiveLegalDocId(docId);
    setActiveNav('legal');
    const url = new URL(window.location.href);
    url.searchParams.delete('pdd');
    if (docId) {
      url.searchParams.set('doc', docId);
    } else {
      url.searchParams.delete('doc');
    }
    window.history.replaceState({}, '', url.toString());
  };

  const openPddDoc = (pddId: string) => {
    setActivePddId(pddId);
    setActiveNav('pdd');
    const url = new URL(window.location.href);
    url.searchParams.delete('doc');
    url.searchParams.set('pdd', pddId);
    window.history.replaceState({}, '', url.toString());
  };

  if (checkingSession) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC] dark:bg-[#0B0F17] text-slate-500 dark:text-slate-400 text-sm">
        Восстановление сессии...
      </div>
    );
  }

  if (!profile) {
    return (
      <AuthGate
        theme={theme}
        onToggleTheme={toggleTheme}
        onAuthenticated={(prof, msgs) => {
          setProfile(prof);
          setMessages(msgs);
        }}
      />
    );
  }

  const activeChat = profile.chats.find((c) => c.chat_id === profile.active_chat_id) || null;

  // Message displayed inside Right Source Inspector (selected or latest assistant reply)
  const inspectedMessage: ChatMessage | null =
    inspectedMsgIndex !== null && messages[inspectedMsgIndex]?.role === 'assistant'
      ? messages[inspectedMsgIndex]
      : [...messages].reverse().find((m) => m.role === 'assistant') || null;

  const jobForCurrentChat =
    activeJob && activeJob.chatId === profile.active_chat_id ? activeJob : null;

  return (
    <div className="h-screen w-screen overflow-hidden flex bg-[#F8FAFC] dark:bg-[#0B0F17] text-[#0F172A] dark:text-[#F1F5F9]">
      <Sidebar
        theme={theme}
        onToggleTheme={toggleTheme}
        profile={profile}
        activeNav={activeNav}
        onSelectNav={setActiveNav}
        onSelectChat={(id) => void handleSelectChat(id)}
        onCreateChat={() => void handleCreateChat()}
        onTogglePin={(chat) => void handleTogglePin(chat)}
        onRenameChat={(id, title) => void handleRenameChat(id, title)}
        onDeleteChat={(id) => void handleDeleteChat(id)}
        onLogout={() => void handleLogout()}
        stats={stats}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {activeNav === 'chat' && (
        <>
          <ChatView
            theme={theme}
            chatTitle={activeChat?.title || 'Ассистент (Чат)'}
            messages={messages}
            activeJob={jobForCurrentChat}
            inspectorOpen={inspectorOpen}
            inspectedMsgIndex={inspectedMsgIndex}
            onToggleInspector={() => setInspectorOpen((v) => !v)}
            onInspectMessage={(idx) => {
              setInspectedMsgIndex(idx);
              setInspectorOpen(true);
            }}
            onSendMessage={handleSendMessage}
            onOpenLegalDoc={(docId) => openLegalDoc(docId)}
            onOpenPddDoc={(pddId) => openPddDoc(pddId)}
            onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
          />

          <SourceInspector
            message={inspectedMessage}
            theme={theme}
            open={inspectorOpen}
            onClose={() => setInspectorOpen(false)}
            onOpenLegalDoc={(docId) => openLegalDoc(docId)}
            onOpenPddDoc={(pddId) => openPddDoc(pddId)}
          />
        </>
      )}

      {activeNav === 'legal' && (
        <LegalExplorerView
          theme={theme}
          activeDocId={activeLegalDocId}
          onSelectDoc={(docId) => openLegalDoc(docId)}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
        />
      )}

      {activeNav === 'pdd' && (
        <PddExplorerView
          theme={theme}
          activePddId={activePddId}
          onSelectPdd={(pddId) => openPddDoc(pddId)}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
        />
      )}
    </div>
  );
}
