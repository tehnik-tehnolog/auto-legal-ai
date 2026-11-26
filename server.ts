import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import express, { type Request, type Response } from 'express';
import multer from 'multer';
import { b2Storage } from './server/b2Storage';
import {
  CHROMA_DIR,
  DATA_DIR,
  LEGAL_CHAPTERS_FILE,
  PDD_CHAPTERS_FILE,
  SERVER_PORT,
  UI_DIR,
} from './server/config';
import { dbService } from './server/db';
import { extractTextFromFile } from './server/fileExtractor';
import { ragEngine } from './server/ragEngine';
import type { ChatMessage, RAGSourceItem } from './server/types';

interface AsyncRagJob {
  jobId: string;
  email: string;
  chatId: string;
  status: 'started' | 'retrieving' | 'generating' | 'completed' | 'error';
  result?: {
    answer: string;
    sources: RAGSourceItem[];
    topics: string[];
    targets: string[];
    fallback_used: boolean;
    fallback_reason: string | null;
    assistantMessage: ChatMessage;
  };
  renamedTitle?: string | null;
  error?: string;
  createdAt: number;
}

const jobsRegistry = new Map<string, AsyncRagJob>();

function cleanupOldJobs(): void {
  const cutoff = Date.now() - 30 * 60 * 1000;
  for (const [id, job] of jobsRegistry.entries()) {
    if (job.createdAt < cutoff) {
      jobsRegistry.delete(id);
    }
  }
}

async function resolveAuthenticatedEmail(req: Request): Promise<string | null> {
  const token = String(req.headers['x-device-token'] || '').trim();
  if (!token) return null;
  return dbService.resolveDeviceToken(token);
}

async function hydrateAttachmentUrls(messages: ChatMessage[]): Promise<ChatMessage[]> {
  if (!b2Storage.isConfigured()) return messages;
  return Promise.all(
    messages.map(async (m) => {
      if (m.attached_b2_key && !m.attached_download_url) {
        const url = await b2Storage.getPresignedUrl(m.attached_b2_key);
        return { ...m, attached_download_url: url };
      }
      return m;
    })
  );
}

function normalizeUploadedFilename(rawName?: string, utf8Override?: unknown): string {
  const override = typeof utf8Override === 'string' ? utf8Override.trim() : '';
  if (override) return override;
  if (!rawName) return 'document';
  // Fix busboy/multer latin1 mojibake for UTF-8 Cyrillic filenames
  if (!/[а-яА-ЯёЁ]/.test(rawName)) {
    try {
      const decoded = Buffer.from(rawName, 'latin1').toString('utf8');
      if (!decoded.includes('\uFFFD') && /[а-яА-ЯёЁ]/.test(decoded)) {
        return decoded;
      }
    } catch {
      // keep rawName
    }
  }
  return rawName;
}

async function startServer(): Promise<void> {
  const app = express();
  const upload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 20 * 1024 * 1024 },
  });

  app.use(express.json({ limit: '2mb' }));
  app.use('/ui', express.static(UI_DIR));

  // Healthcheck endpoints (Red Hat OpenShift probes & monitoring)
  app.get(['/api/health', '/healthz'], (_req: Request, res: Response) => {
    res.json({
      ok: true,
      b2: b2Storage.isConfigured(),
      b2Sync: b2Storage.getSyncStatus(),
      supabase: dbService.isSupabaseConfigured(),
      kb: ragEngine.getStats(),
    });
  });

  // Silent device auto-login session check
  app.post('/api/auth/session', async (req: Request, res: Response) => {
    try {
      const token = String(req.headers['x-device-token'] || req.body?.deviceToken || '').trim();
      if (!token) {
        res.json({ authenticated: false });
        return;
      }
      const email = await dbService.resolveDeviceToken(token);
      if (!email) {
        res.json({ authenticated: false });
        return;
      }
      const profile = await dbService.getProfileMeta(email);
      const activeId = profile.active_chat_id || profile.chats[0]?.chat_id || '';
      const messages = await hydrateAttachmentUrls(await dbService.getChatMessages(email, activeId));
      res.json({ authenticated: true, profile, messages });
    } catch (err) {
      console.error('[API] /api/auth/session error:', err);
      res.json({ authenticated: false });
    }
  });

  // Register or login with Name + Email
  app.post('/api/auth/login', async (req: Request, res: Response) => {
    try {
      const email = String(req.body?.email || '').trim().toLowerCase();
      const name = String(req.body?.name || '').trim();

      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        res.status(400).json({ error: 'Пожалуйста, введите корректный адрес электронной почты.' });
        return;
      }
      if (!name) {
        res.status(400).json({ error: 'Пожалуйста, введите ваше имя.' });
        return;
      }

      const data = await dbService.registerOrLogin(email, name);
      const hydrated = await hydrateAttachmentUrls(data.messages);
      res.json({
        authenticated: true,
        profile: data.profile,
        messages: hydrated,
        deviceToken: data.deviceToken,
      });
    } catch (err) {
      console.error('[API] /api/auth/login error:', err);
      res.status(500).json({ error: 'Не удалось выполнить вход. Попробуйте ещё раз.' });
    }
  });

  // Guest sign-in without email/name registration
  app.post('/api/auth/guest', async (_req: Request, res: Response) => {
    try {
      const guestEmail = `guest_${crypto.randomBytes(6).toString('hex')}@guest.local`;
      const data = await dbService.registerOrLogin(guestEmail, 'Гость');
      res.json({
        authenticated: true,
        profile: data.profile,
        messages: data.messages || [],
        deviceToken: data.deviceToken,
      });
    } catch (err) {
      console.error('[API] /api/auth/guest error:', err);
      res.status(500).json({ error: 'Не удалось войти как гость.' });
    }
  });

  // Logout & forget device token
  app.post('/api/auth/logout', async (req: Request, res: Response) => {
    try {
      const token = String(req.headers['x-device-token'] || req.body?.deviceToken || '').trim();
      await dbService.revokeDeviceToken(token);
      res.json({ ok: true });
    } catch {
      res.json({ ok: true });
    }
  });

  // KB stats & manual B2 re-sync endpoint
  app.get('/api/kb/stats', (_req: Request, res: Response) => {
    res.json(ragEngine.getStats());
  });

  app.post('/api/kb/sync', async (_req: Request, res: Response) => {
    if (!b2Storage.isConfigured()) {
      res.status(400).json({ error: 'Backblaze B2 is not configured.' });
      return;
    }
    const summary = await b2Storage.syncKbFromB2(DATA_DIR);
    ragEngine.reload();
    res.json({ summary, status: b2Storage.getSyncStatus(), kb: ragEngine.getStats() });
  });

  // Legal docs catalog & single-doc lookup
  app.get('/api/kb/legal', (req: Request, res: Response) => {
    const allDocs = ragEngine.getLegalDocs();
    const docId = String(req.query.docId || '').trim();
    const code = String(req.query.code || 'Все акты').trim();

    const codes = Array.from(
      new Set(allDocs.map((d) => d.code || d.section || '').filter(Boolean))
    ).sort();
    const docsForCategories =
      code && code !== 'Все акты'
        ? allDocs.filter((d) => d.code === code || d.section === code)
        : allDocs;
    const categories = Array.from(
      new Set(docsForCategories.map((d) => d.category || '').filter(Boolean))
    ).sort();

    if (docId) {
      const cleanId = docId.replace(/^(?:#?doc-legal_|#?legal_|#)/, '');
      const found =
        allDocs.find(
          (d) =>
            d.parent_id === docId ||
            d.doc_id === docId ||
            d.parent_id === cleanId ||
            d.doc_id === cleanId
        ) || null;
      res.json({
        doc: found,
        codes,
        categories,
        total: allDocs.length,
      });
      return;
    }

    const category = String(req.query.category || 'Все категории').trim();
    const q = String(req.query.q || '').trim().toLowerCase();

    let filtered = docsForCategories;
    if (category && category !== 'Все категории') {
      filtered = filtered.filter((d) => d.category === category);
    }
    if (q) {
      filtered = filtered.filter(
        (d) =>
          (d.title || '').toLowerCase().includes(q) ||
          (d.chapter_number || '').toLowerCase().includes(q) ||
          (d.article_number || '').toLowerCase().includes(q) ||
          (d.body || '').toLowerCase().includes(q) ||
          (d.parent_id || '').toLowerCase().includes(q)
      );
    }

    // If exactly 1 article matches, return full body; otherwise return lightweight list items
    if (filtered.length === 1) {
      res.json({
        items: [],
        singleDoc: filtered[0],
        totalFiltered: 1,
        codes,
        categories,
      });
      return;
    }

    const summaryItems = filtered.slice(0, 300).map((d) => ({
      parent_id: d.parent_id,
      doc_id: d.doc_id,
      code: d.code || d.section || 'ГК РФ',
      chapter_number: d.chapter_number || '',
      article_number: d.article_number || '',
      title: d.title,
      category: d.category || '',
      priority_level: d.priority_level || 'standard',
    }));

    res.json({
      items: summaryItems,
      singleDoc: null,
      totalFiltered: filtered.length,
      truncated: filtered.length > 300,
      codes,
      categories,
    });
  });

  // PDD chapters catalog & single chapter lookup
  app.get('/api/kb/pdd', (req: Request, res: Response) => {
    const allChapters = ragEngine.getPddDocs();
    const pddId = String(req.query.pddId || '').trim();
    const toc = allChapters.map((c) => ({
      parent_id: c.parent_id,
      chapter_number: c.chapter_number || '',
      chapter_title: c.chapter_title || c.title || '',
      title: c.title,
    }));

    let activeChapter = allChapters[0] || null;
    if (pddId) {
      const cleanId = pddId.replace(/^(?:#?doc-pdd_|#)/, '');
      const match = allChapters.find(
        (c) =>
          c.parent_id === pddId ||
          c.doc_id === pddId ||
          c.parent_id === cleanId ||
          c.doc_id === cleanId
      );
      if (match) activeChapter = match;
    }

    res.json({
      toc,
      activeChapter,
      total: allChapters.length,
    });
  });

  // Chat management endpoints
  app.get('/api/chats/profile', async (req: Request, res: Response) => {
    const email = await resolveAuthenticatedEmail(req);
    if (!email) {
      res.status(401).json({ error: 'Необходима авторизация' });
      return;
    }
    const profile = await dbService.getProfileMeta(email);
    const activeId = profile.active_chat_id || profile.chats[0]?.chat_id || '';
    const messages = await hydrateAttachmentUrls(await dbService.getChatMessages(email, activeId));
    res.json({ profile, messages });
  });

  app.post('/api/chats', async (req: Request, res: Response) => {
    const email = await resolveAuthenticatedEmail(req);
    if (!email) {
      res.status(401).json({ error: 'Необходима авторизация' });
      return;
    }
    const created = await dbService.createChat(email, req.body?.title);
    const profile = await dbService.getProfileMeta(email);
    res.json({ chat: created, profile, messages: [] });
  });

  app.post('/api/chats/:chatId/activate', async (req: Request, res: Response) => {
    const email = await resolveAuthenticatedEmail(req);
    if (!email) {
      res.status(401).json({ error: 'Необходима авторизация' });
      return;
    }
    const chatId = String(req.params.chatId || '');
    await dbService.setActiveChat(email, chatId);
    const profile = await dbService.getProfileMeta(email);
    const messages = await hydrateAttachmentUrls(await dbService.getChatMessages(email, chatId));
    res.json({ profile, messages });
  });

  app.patch('/api/chats/:chatId', async (req: Request, res: Response) => {
    const email = await resolveAuthenticatedEmail(req);
    if (!email) {
      res.status(401).json({ error: 'Необходима авторизация' });
      return;
    }
    const chatId = String(req.params.chatId || '');
    await dbService.updateChat(email, chatId, {
      title: typeof req.body?.title === 'string' ? req.body.title : undefined,
      pinned: typeof req.body?.pinned === 'boolean' ? req.body.pinned : undefined,
    });
    const profile = await dbService.getProfileMeta(email);
    res.json({ profile });
  });

  app.delete('/api/chats/:chatId', async (req: Request, res: Response) => {
    const email = await resolveAuthenticatedEmail(req);
    if (!email) {
      res.status(401).json({ error: 'Необходима авторизация' });
      return;
    }
    const chatId = String(req.params.chatId || '');
    const deleted = await dbService.deleteChat(email, chatId);
    const profile = await dbService.getProfileMeta(email);
    const activeId = profile.active_chat_id || profile.chats[0]?.chat_id || '';
    const messages = await hydrateAttachmentUrls(await dbService.getChatMessages(email, activeId));
    res.json({ deleted, profile, messages });
  });

  // Submit RAG question + optional file attachment -> async background job
  app.post('/api/chat/ask', upload.single('file'), async (req: Request, res: Response) => {
    try {
      const email = await resolveAuthenticatedEmail(req);
      if (!email) {
        res.status(401).json({ error: 'Необходима авторизация' });
        return;
      }

      const prompt = String(req.body?.prompt || '').trim();
      const chatId = String(req.body?.chatId || '').trim();
      if (!prompt || !chatId) {
        res.status(400).json({ error: 'Укажите текст вопроса и идентификатор чата.' });
        return;
      }

      cleanupOldJobs();

      let extractedText = '';
      let attachedFilename: string | null = null;
      let attachedB2Key: string | null = null;
      let attachedDownloadUrl: string | null = null;

      if (req.file) {
        attachedFilename = normalizeUploadedFilename(
          req.file.originalname,
          req.body?.originalFilename
        );
        extractedText = await extractTextFromFile(req.file.buffer, attachedFilename);

        if (b2Storage.isConfigured()) {
          attachedB2Key = await b2Storage.uploadUserAttachment(
            email,
            chatId,
            attachedFilename,
            req.file.buffer,
            req.file.mimetype
          );
          if (attachedB2Key) {
            await dbService.recordDocument(
              attachedB2Key,
              email,
              chatId,
              attachedFilename,
              req.file.size
            );
            attachedDownloadUrl = await b2Storage.getPresignedUrl(attachedB2Key);
          }
        }
      }

      const userMessage: ChatMessage = {
        role: 'user',
        content: prompt,
        attached_filename: attachedFilename,
        attached_chars: extractedText.length,
        attached_b2_key: attachedB2Key,
        attached_download_url: attachedDownloadUrl,
      };
      await dbService.appendMessage(email, chatId, userMessage);

      const jobId = `job_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`;
      const job: AsyncRagJob = {
        jobId,
        email,
        chatId,
        status: 'started',
        createdAt: Date.now(),
      };
      jobsRegistry.set(jobId, job);

      // Run RAG pipeline asynchronously without blocking the HTTP response
      void (async () => {
        try {
          const ragRes = await ragEngine.answerQuery(prompt, extractedText, (stage) => {
            job.status = stage;
          });

          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: ragRes.answer,
            sources: ragRes.sources,
            topics: ragRes.topics,
            targets: ragRes.targets,
            fallback_used: ragRes.fallback_used,
            fallback_reason: ragRes.fallback_reason,
          };

          await dbService.appendMessage(email, chatId, assistantMessage);

          let renamedTitle: string | null = null;
          if (ragRes.topics.length > 0) {
            const meta = await dbService.getProfileMeta(email);
            const targetChat = meta.chats.find((c) => c.chat_id === chatId);
            if (
              targetChat &&
              (targetChat.title.includes('Новый диалог') || targetChat.title === 'Новый чат')
            ) {
              const firstTopic = ragRes.topics[0].trim();
              const capitalized =
                firstTopic.charAt(0).toUpperCase() + firstTopic.slice(1);
              await dbService.updateChat(email, chatId, { title: capitalized });
              renamedTitle = capitalized;
            }
          }

          job.renamedTitle = renamedTitle;
          job.result = { ...ragRes, assistantMessage };
          job.status = 'completed';
        } catch (err) {
          job.status = 'error';
          job.error = err instanceof Error ? err.message : String(err);
        }
      })();

      res.json({ jobId, userMessage });
    } catch (err) {
      console.error('[API] /api/chat/ask error:', err);
      res.status(500).json({ error: 'Ошибка при отправке вопроса.' });
    }
  });

  app.get('/api/chat/jobs/:jobId', async (req: Request, res: Response) => {
    const email = await resolveAuthenticatedEmail(req);
    if (!email) {
      res.status(401).json({ error: 'Необходима авторизация' });
      return;
    }
    const job = jobsRegistry.get(String(req.params.jobId || ''));
    if (!job || job.email !== email) {
      res.status(404).json({ error: 'Задача не найдена' });
      return;
    }
    res.json({
      jobId: job.jobId,
      chatId: job.chatId,
      status: job.status,
      result: job.result || null,
      renamedTitle: job.renamedTitle || null,
      error: job.error || null,
    });
  });

  // Frontend Vite / Static Production Serving
  if (process.env.NODE_ENV !== 'production') {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distDir = path.join(process.cwd(), 'dist');
    app.use(express.static(distDir));
    app.get('*', (_req: Request, res: Response) => {
      res.sendFile(path.join(distDir, 'index.html'));
    });
  }

  app.listen(SERVER_PORT, '0.0.0.0', () => {
    console.log(`[Server] Legal RAG Express + React listening on http://0.0.0.0:${SERVER_PORT}`);
    // Hydrate KB from Backblaze B2 if any core KB file is missing and warm up BM25 indices in background
    void (async () => {
      const hasCoreKb = () =>
        fs.existsSync(LEGAL_CHAPTERS_FILE) &&
        fs.existsSync(PDD_CHAPTERS_FILE) &&
        fs.existsSync(path.join(CHROMA_DIR, 'legal_laws_chunks.json')) &&
        fs.existsSync(path.join(CHROMA_DIR, 'parent_store.json'));

      const needsB2Sync = !hasCoreKb();

      if (b2Storage.isConfigured() && (needsB2Sync || process.env.B2_AUTO_SYNC === 'true')) {
        console.log(`[B2] Starting KB sync into ${DATA_DIR}...`);
        const summary = await b2Storage.syncKbFromB2(DATA_DIR);
        if (needsB2Sync && summary.errors > 0 && summary.downloaded === 0) {
          console.warn('[B2] Initial sync encountered errors; retrying once in 5s...');
          await new Promise((r) => setTimeout(r, 5000));
          await b2Storage.syncKbFromB2(DATA_DIR);
        }
        ragEngine.reload();
      } else {
        if (needsB2Sync && !b2Storage.isConfigured()) {
          console.warn('[B2] Core KB files are missing and Backblaze B2 env vars are not set.');
        }
        ragEngine.ensureLoaded();
      }
      if (dbService.isSupabaseConfigured()) {
        await dbService.initSchema();
      }
    })();
  });
}

startServer().catch((err) => {
  console.error('[Server] Fatal startup error:', err);
  process.exit(1);
});
