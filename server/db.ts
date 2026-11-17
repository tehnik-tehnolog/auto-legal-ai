import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { Pool } from 'pg';
import {
  CHATS_DIR,
  DATABASE_URL,
  SUPABASE_DBNAME,
  SUPABASE_HOST,
  SUPABASE_PASSWORD,
  SUPABASE_PORT,
  SUPABASE_USER,
} from './config';
import type { ChatMessage, ChatMeta, UserProfileMeta } from './types';

interface LocalProfileFile {
  user_id: string;
  email: string;
  user_name: string;
  active_chat_id: string | null;
  chats: Array<ChatMeta & { messages: ChatMessage[] }>;
}

function nowFormatted(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function buildInitialChat(title = 'Новый чат'): ChatMeta & { messages: ChatMessage[] } {
  const ts = new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 17);
  const rand = crypto.randomBytes(3).toString('hex');
  return {
    chat_id: `chat_${ts}_${rand}`,
    title,
    created_at: nowFormatted(),
    pinned: false,
    messages: [],
  };
}

function hashDeviceToken(token: string): string {
  return crypto.createHash('sha256').update(token).digest('hex');
}

class DatabaseService {
  private pool: Pool | null = null;
  private schemaInitialized = false;
  private supabaseUnavailable = false;
  private devicesFile = path.join(CHATS_DIR, '_devices.json');

  isSupabaseConfigured(): boolean {
    if (this.supabaseUnavailable) return false;
    if (DATABASE_URL) return true;
    return Boolean(SUPABASE_HOST && SUPABASE_USER && SUPABASE_PASSWORD);
  }

  private getPool(): Pool | null {
    if (!this.isSupabaseConfigured()) return null;
    if (this.pool) return this.pool;

    if (DATABASE_URL) {
      this.pool = new Pool({
        connectionString: DATABASE_URL,
        ssl: DATABASE_URL.includes('localhost') ? undefined : { rejectUnauthorized: false },
        connectionTimeoutMillis: 8000,
        max: 5,
      });
    } else {
      this.pool = new Pool({
        host: SUPABASE_HOST,
        port: SUPABASE_PORT,
        user: SUPABASE_USER,
        password: SUPABASE_PASSWORD,
        database: SUPABASE_DBNAME || 'postgres',
        ssl: { rejectUnauthorized: false },
        connectionTimeoutMillis: 8000,
        max: 5,
      });
    }
    return this.pool;
  }

  async initSchema(): Promise<boolean> {
    if (!this.isSupabaseConfigured()) return false;
    if (this.schemaInitialized) return true;
    const pool = this.getPool();
    if (!pool) return false;

    const ddl = `
      CREATE TABLE IF NOT EXISTS rag_users (
        email TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        active_chat_id TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        last_login_at TIMESTAMPTZ DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS rag_chats (
        chat_id TEXT PRIMARY KEY,
        user_email TEXT NOT NULL REFERENCES rag_users(email) ON DELETE CASCADE,
        title TEXT NOT NULL,
        pinned BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
      );

      CREATE INDEX IF NOT EXISTS idx_rag_chats_user_email ON rag_chats(user_email);

      CREATE TABLE IF NOT EXISTS rag_messages (
        id SERIAL PRIMARY KEY,
        chat_id TEXT NOT EXISTS_PLACEHOLDER,
        role TEXT NOT NULL,
        content TEXT NOT NULL
      );
    `;
    void ddl;

    const cleanDdl = `
      CREATE TABLE IF NOT EXISTS rag_users (
        email TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        active_chat_id TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        last_login_at TIMESTAMPTZ DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS rag_chats (
        chat_id TEXT PRIMARY KEY,
        user_email TEXT NOT NULL REFERENCES rag_users(email) ON DELETE CASCADE,
        title TEXT NOT NULL,
        pinned BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
      );

      CREATE INDEX IF NOT EXISTS idx_rag_chats_user_email ON rag_chats(user_email);

      CREATE TABLE IF NOT EXISTS rag_messages (
        id SERIAL PRIMARY KEY,
        chat_id TEXT NOT NULL REFERENCES rag_chats(chat_id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        sources JSONB DEFAULT '[]'::jsonb,
        topics JSONB DEFAULT '[]'::jsonb,
        targets JSONB DEFAULT '[]'::jsonb,
        attached_filename TEXT,
        attached_chars INTEGER DEFAULT 0,
        attached_b2_key TEXT,
        fallback_used BOOLEAN DEFAULT FALSE,
        fallback_reason TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );

      CREATE INDEX IF NOT EXISTS idx_rag_messages_chat_id ON rag_messages(chat_id);

      CREATE TABLE IF NOT EXISTS rag_documents (
        doc_key TEXT PRIMARY KEY,
        user_email TEXT NOT NULL,
        chat_id TEXT,
        filename TEXT NOT NULL,
        size_bytes BIGINT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );

      CREATE TABLE IF NOT EXISTS rag_devices (
        token_hash TEXT PRIMARY KEY,
        user_email TEXT NOT NULL REFERENCES rag_users(email) ON DELETE CASCADE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        last_seen_at TIMESTAMPTZ DEFAULT NOW()
      );
    `;

    try {
      await pool.query(cleanDdl);
      this.schemaInitialized = true;
      return true;
    } catch (err) {
      console.error('[DB] Supabase initSchema failed, using local JSON fallback:', err);
      this.supabaseUnavailable = true;
      return false;
    }
  }

  // --- Local JSON helpers ---
  private getLocalUserFile(email: string): string {
    const safeId = email.trim().toLowerCase().replace(/[^a-z0-9_.-]/g, '_');
    return path.join(CHATS_DIR, `${safeId}.json`);
  }

  private readLocalProfile(email: string, defaultName = 'Юрист'): LocalProfileFile {
    const normEmail = email.trim().toLowerCase();
    const filePath = this.getLocalUserFile(normEmail);
    if (fs.existsSync(filePath)) {
      try {
        const parsed = JSON.parse(fs.readFileSync(filePath, 'utf-8')) as LocalProfileFile;
        if (parsed && Array.isArray(parsed.chats)) {
          if (defaultName && defaultName !== 'Юрист' && (!parsed.user_name || parsed.user_name === 'Юрист')) {
            parsed.user_name = defaultName;
          }
          if (parsed.chats.length === 0) {
            const init = buildInitialChat();
            parsed.chats.push(init);
            parsed.active_chat_id = init.chat_id;
            this.writeLocalProfile(parsed);
          }
          return parsed;
        }
      } catch {
        // rewrite cleanly
      }
    }
    const initChat = buildInitialChat();
    const created: LocalProfileFile = {
      user_id: normEmail,
      email: normEmail,
      user_name: defaultName,
      active_chat_id: initChat.chat_id,
      chats: [initChat],
    };
    this.writeLocalProfile(created);
    return created;
  }

  private writeLocalProfile(profile: LocalProfileFile): void {
    const filePath = this.getLocalUserFile(profile.email || profile.user_id);
    fs.writeFileSync(filePath, JSON.stringify(profile, null, 2), 'utf-8');
  }

  private readLocalDevices(): Record<string, string> {
    if (!fs.existsSync(this.devicesFile)) return {};
    try {
      return JSON.parse(fs.readFileSync(this.devicesFile, 'utf-8')) as Record<string, string>;
    } catch {
      return {};
    }
  }

  private writeLocalDevices(map: Record<string, string>): void {
    fs.writeFileSync(this.devicesFile, JSON.stringify(map, null, 2), 'utf-8');
  }

  // --- Public Methods ---
  async registerOrLogin(
    email: string,
    name: string
  ): Promise<{ profile: UserProfileMeta; messages: ChatMessage[]; deviceToken: string }> {
    const normEmail = email.trim().toLowerCase();
    const cleanName = name.trim() || normEmail.split('@')[0];
    const deviceToken = crypto.randomBytes(32).toString('hex');
    const tokenHash = hashDeviceToken(deviceToken);

    if (await this.initSchema()) {
      const pool = this.getPool()!;
      const client = await pool.connect();
      try {
        await client.query('BEGIN');
        const userRes = await client.query<{ email: string; name: string; active_chat_id: string | null }>(
          'SELECT email, name, active_chat_id FROM rag_users WHERE email = $1',
          [normEmail]
        );
        if (userRes.rows.length > 0) {
          await client.query(
            `UPDATE rag_users
             SET name = CASE WHEN $1 <> '' THEN $1 ELSE name END,
                 last_login_at = NOW()
             WHERE email = $2`,
            [cleanName, normEmail]
          );
        } else {
          const initChat = buildInitialChat();
          await client.query(
            'INSERT INTO rag_users (email, name, active_chat_id) VALUES ($1, $2, $3)',
            [normEmail, cleanName, initChat.chat_id]
          );
          await client.query(
            'INSERT INTO rag_chats (chat_id, user_email, title, pinned) VALUES ($1, $2, $3, FALSE)',
            [initChat.chat_id, normEmail, initChat.title]
          );
        }
        await client.query(
          'INSERT INTO rag_devices (token_hash, user_email) VALUES ($1, $2) ON CONFLICT (token_hash) DO NOTHING',
          [tokenHash, normEmail]
        );
        await client.query('COMMIT');
      } catch (err) {
        await client.query('ROLLBACK');
        console.error('[DB] registerOrLogin error:', err);
      } finally {
        client.release();
      }

      const meta = await this.getProfileMeta(normEmail, cleanName);
      const activeId = meta.active_chat_id || meta.chats[0]?.chat_id || '';
      const messages = activeId ? await this.getChatMessages(normEmail, activeId) : [];
      return { profile: meta, messages, deviceToken };
    }

    // Local JSON fallback
    const localProf = this.readLocalProfile(normEmail, cleanName);
    if (cleanName && localProf.user_name !== cleanName) {
      localProf.user_name = cleanName;
      this.writeLocalProfile(localProf);
    }
    const devMap = this.readLocalDevices();
    devMap[tokenHash] = normEmail;
    this.writeLocalDevices(devMap);

    const meta = this.toMeta(localProf);
    const activeChat =
      localProf.chats.find((c) => c.chat_id === meta.active_chat_id) || localProf.chats[0];
    return {
      profile: meta,
      messages: activeChat ? activeChat.messages : [],
      deviceToken,
    };
  }

  async resolveDeviceToken(deviceToken: string): Promise<string | null> {
    if (!deviceToken) return null;
    const tokenHash = hashDeviceToken(deviceToken);

    if (await this.initSchema()) {
      const pool = this.getPool()!;
      try {
        const res = await pool.query<{ user_email: string }>(
          'SELECT user_email FROM rag_devices WHERE token_hash = $1',
          [tokenHash]
        );
        if (res.rows[0]?.user_email) {
          pool
            .query('UPDATE rag_devices SET last_seen_at = NOW() WHERE token_hash = $1', [tokenHash])
            .catch(() => {});
          return res.rows[0].user_email;
        }
        return null;
      } catch {
        return null;
      }
    }

    const devMap = this.readLocalDevices();
    return devMap[tokenHash] || null;
  }

  async revokeDeviceToken(deviceToken: string): Promise<void> {
    if (!deviceToken) return;
    const tokenHash = hashDeviceToken(deviceToken);

    if (await this.initSchema()) {
      const pool = this.getPool()!;
      await pool.query('DELETE FROM rag_devices WHERE token_hash = $1', [tokenHash]).catch(() => {});
      return;
    }

    const devMap = this.readLocalDevices();
    if (devMap[tokenHash]) {
      delete devMap[tokenHash];
      this.writeLocalDevices(devMap);
    }
  }

  private toMeta(localProf: LocalProfileFile): UserProfileMeta {
    const sorted = [...localProf.chats].sort((a, b) => Number(b.pinned) - Number(a.pinned));
    const activeId =
      localProf.active_chat_id && sorted.some((c) => c.chat_id === localProf.active_chat_id)
        ? localProf.active_chat_id
        : sorted[0]?.chat_id || null;
    return {
      user_id: localProf.user_id,
      email: localProf.email,
      user_name: localProf.user_name,
      active_chat_id: activeId,
      chats: sorted.map(({ chat_id, title, created_at, pinned }) => ({
        chat_id,
        title,
        created_at,
        pinned: Boolean(pinned),
      })),
    };
  }

  async getProfileMeta(email: string, defaultName = 'Юрист'): Promise<UserProfileMeta> {
    const normEmail = email.trim().toLowerCase();

    if (await this.initSchema()) {
      const pool = this.getPool()!;
      const userRes = await pool.query<{ email: string; name: string; active_chat_id: string | null }>(
        'SELECT email, name, active_chat_id FROM rag_users WHERE email = $1',
        [normEmail]
      );
      if (userRes.rows.length === 0) {
        const created = await this.registerOrLogin(normEmail, defaultName);
        return created.profile;
      }
      const user = userRes.rows[0];
      const chatsRes = await pool.query<{
        chat_id: string;
        title: string;
        pinned: boolean;
        created_at: string;
      }>(
        `SELECT chat_id, title, pinned, TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created_at
         FROM rag_chats
         WHERE user_email = $1
         ORDER BY pinned DESC, updated_at DESC, created_at DESC`,
        [normEmail]
      );
      let chats: ChatMeta[] = chatsRes.rows;
      let activeId = user.active_chat_id;

      if (chats.length === 0) {
        const init = buildInitialChat();
        await pool.query(
          'INSERT INTO rag_chats (chat_id, user_email, title, pinned) VALUES ($1, $2, $3, FALSE)',
          [init.chat_id, normEmail, init.title]
        );
        await pool.query('UPDATE rag_users SET active_chat_id = $1 WHERE email = $2', [
          init.chat_id,
          normEmail,
        ]);
        chats = [{ chat_id: init.chat_id, title: init.title, created_at: init.created_at, pinned: false }];
        activeId = init.chat_id;
      } else if (!activeId || !chats.some((c) => c.chat_id === activeId)) {
        activeId = chats[0].chat_id;
      }

      return {
        user_id: user.email,
        email: user.email,
        user_name: user.name,
        active_chat_id: activeId,
        chats,
      };
    }

    const localProf = this.readLocalProfile(normEmail, defaultName);
    return this.toMeta(localProf);
  }

  async getChatMessages(email: string, chatId: string): Promise<ChatMessage[]> {
    if (!chatId) return [];

    if (await this.initSchema()) {
      const pool = this.getPool()!;
      const res = await pool.query<{
        id: number;
        role: 'user' | 'assistant';
        content: string;
        sources: ChatMessage['sources'];
        topics: string[];
        targets: string[];
        attached_filename: string | null;
        attached_chars: number;
        attached_b2_key: string | null;
        fallback_used: boolean;
        fallback_reason: string | null;
        created_at: string;
      }>(
        `SELECT id, role, content, sources, topics, targets,
                attached_filename, attached_chars, attached_b2_key,
                fallback_used, fallback_reason,
                TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') AS created_at
         FROM rag_messages
         WHERE chat_id = $1
         ORDER BY id ASC`,
        [chatId]
      );
      return res.rows.map((r) => ({
        id: String(r.id),
        role: r.role,
        content: r.content,
        sources: r.sources || [],
        topics: r.topics || [],
        targets: r.targets || [],
        attached_filename: r.attached_filename,
        attached_chars: r.attached_chars || 0,
        attached_b2_key: r.attached_b2_key,
        fallback_used: Boolean(r.fallback_used),
        fallback_reason: r.fallback_reason,
        created_at: r.created_at,
      }));
    }

    const localProf = this.readLocalProfile(email);
    const found = localProf.chats.find((c) => c.chat_id === chatId);
    return found ? found.messages || [] : [];
  }

  async createChat(email: string, title?: string): Promise<ChatMeta> {
    const normEmail = email.trim().toLowerCase();
    const fallbackTitle =
      title?.trim() ||
      `Новый диалог (${new Date().toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })} ${new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })})`;
    const newChat = buildInitialChat(fallbackTitle);

    if (await this.initSchema()) {
      const pool = this.getPool()!;
      await pool.query(
        'INSERT INTO rag_chats (chat_id, user_email, title, pinned) VALUES ($1, $2, $3, FALSE)',
        [newChat.chat_id, normEmail, newChat.title]
      );
      await pool.query('UPDATE rag_users SET active_chat_id = $1 WHERE email = $2', [
        newChat.chat_id,
        normEmail,
      ]);
      return {
        chat_id: newChat.chat_id,
        title: newChat.title,
        created_at: newChat.created_at,
        pinned: false,
      };
    }

    const localProf = this.readLocalProfile(normEmail);
    localProf.chats.unshift(newChat);
    localProf.active_chat_id = newChat.chat_id;
    this.writeLocalProfile(localProf);
    return {
      chat_id: newChat.chat_id,
      title: newChat.title,
      created_at: newChat.created_at,
      pinned: false,
    };
  }

  async setActiveChat(email: string, chatId: string): Promise<void> {
    const normEmail = email.trim().toLowerCase();
    if (await this.initSchema()) {
      const pool = this.getPool()!;
      await pool.query('UPDATE rag_users SET active_chat_id = $1 WHERE email = $2', [
        chatId,
        normEmail,
      ]);
      return;
    }

    const localProf = this.readLocalProfile(normEmail);
    localProf.active_chat_id = chatId;
    this.writeLocalProfile(localProf);
  }

  async updateChat(
    email: string,
    chatId: string,
    updates: { title?: string; pinned?: boolean }
  ): Promise<void> {
    const normEmail = email.trim().toLowerCase();
    if (await this.initSchema()) {
      const pool = this.getPool()!;
      if (typeof updates.title === 'string' && updates.title.trim()) {
        await pool.query(
          'UPDATE rag_chats SET title = $1, updated_at = NOW() WHERE chat_id = $2 AND user_email = $3',
          [updates.title.trim(), chatId, normEmail]
        );
      }
      if (typeof updates.pinned === 'boolean') {
        await pool.query(
          'UPDATE rag_chats SET pinned = $1 WHERE chat_id = $2 AND user_email = $3',
          [updates.pinned, chatId, normEmail]
        );
      }
      return;
    }

    const localProf = this.readLocalProfile(normEmail);
    for (const c of localProf.chats) {
      if (c.chat_id === chatId) {
        if (typeof updates.title === 'string' && updates.title.trim()) {
          c.title = updates.title.trim();
        }
        if (typeof updates.pinned === 'boolean') {
          c.pinned = updates.pinned;
        }
        break;
      }
    }
    this.writeLocalProfile(localProf);
  }

  async deleteChat(email: string, chatId: string): Promise<boolean> {
    const normEmail = email.trim().toLowerCase();
    if (await this.initSchema()) {
      const pool = this.getPool()!;
      const countRes = await pool.query<{ cnt: string }>(
        'SELECT COUNT(*) AS cnt FROM rag_chats WHERE user_email = $1',
        [normEmail]
      );
      if (Number(countRes.rows[0]?.cnt || 0) <= 1) return false;

      await pool.query('DELETE FROM rag_chats WHERE chat_id = $1 AND user_email = $2', [
        chatId,
        normEmail,
      ]);
      const remRes = await pool.query<{ chat_id: string }>(
        `SELECT chat_id FROM rag_chats WHERE user_email = $1 ORDER BY pinned DESC, updated_at DESC LIMIT 1`,
        [normEmail]
      );
      if (remRes.rows[0]?.chat_id) {
        await pool.query(
          'UPDATE rag_users SET active_chat_id = $1 WHERE email = $2 AND (active_chat_id = $3 OR active_chat_id IS NULL)',
          [remRes.rows[0].chat_id, normEmail, chatId]
        );
      }
      return true;
    }

    const localProf = this.readLocalProfile(normEmail);
    if (localProf.chats.length <= 1) return false;
    localProf.chats = localProf.chats.filter((c) => c.chat_id !== chatId);
    if (localProf.active_chat_id === chatId && localProf.chats[0]) {
      localProf.active_chat_id = localProf.chats[0].chat_id;
    }
    this.writeLocalProfile(localProf);
    return true;
  }

  async appendMessage(email: string, chatId: string, msg: ChatMessage): Promise<void> {
    const normEmail = email.trim().toLowerCase();
    if (await this.initSchema()) {
      const pool = this.getPool()!;
      await pool.query(
        `INSERT INTO rag_messages (
          chat_id, role, content, sources, topics, targets,
          attached_filename, attached_chars, attached_b2_key,
          fallback_used, fallback_reason
        ) VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7, $8, $9, $10, $11)`,
        [
          chatId,
          msg.role,
          msg.content,
          JSON.stringify(msg.sources || []),
          JSON.stringify(msg.topics || []),
          JSON.stringify(msg.targets || []),
          msg.attached_filename || null,
          msg.attached_chars || 0,
          msg.attached_b2_key || null,
          Boolean(msg.fallback_used),
          msg.fallback_reason || null,
        ]
      );
      await pool.query('UPDATE rag_chats SET updated_at = NOW() WHERE chat_id = $1', [chatId]);
      return;
    }

    const localProf = this.readLocalProfile(normEmail);
    const target = localProf.chats.find((c) => c.chat_id === chatId);
    if (target) {
      target.messages.push({ ...msg, created_at: msg.created_at || nowFormatted() });
      this.writeLocalProfile(localProf);
    }
  }

  async recordDocument(
    docKey: string,
    email: string,
    chatId: string,
    filename: string,
    sizeBytes: number
  ): Promise<void> {
    if (await this.initSchema()) {
      const pool = this.getPool()!;
      await pool
        .query(
          `INSERT INTO rag_documents (doc_key, user_email, chat_id, filename, size_bytes)
           VALUES ($1, $2, $3, $4, $5) ON CONFLICT (doc_key) DO NOTHING`,
          [docKey, email.trim().toLowerCase(), chatId, filename, sizeBytes]
        )
        .catch(() => {});
    }
  }
}

export const dbService = new DatabaseService();
