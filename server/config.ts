import path from 'node:path';
import fs from 'node:fs';
import dotenv from 'dotenv';

dotenv.config();

export const BASE_DIR = process.cwd();
export const DATA_DIR = path.resolve(process.env.RAG_DATA_DIR || path.join(BASE_DIR, 'data'));
export const CHROMA_DIR = path.join(DATA_DIR, 'chroma');
export const LEGAL_DIR = path.join(DATA_DIR, 'legal');
export const COURT_DIR = path.join(DATA_DIR, 'court');
export const CARS_DIR = path.join(DATA_DIR, 'cars');
export const NEWS_DIR = path.join(DATA_DIR, 'news');
export const PDD_DIR = path.join(DATA_DIR, 'pdd');
export const CHATS_DIR = path.join(DATA_DIR, 'chats');
export const LOGS_DIR = path.join(BASE_DIR, 'logs');
export const UI_DIR = path.join(BASE_DIR, 'ui');

export const LEGAL_CHAPTERS_FILE = path.join(LEGAL_DIR, 'legal_chapters.jsonl');
export const LEGAL_JSONL_FILE = path.join(LEGAL_DIR, 'laws_gk_nk.jsonl');
export const PDD_CHAPTERS_FILE = path.join(PDD_DIR, 'pdd_chapters.jsonl');

for (const dirPath of [LEGAL_DIR, COURT_DIR, CARS_DIR, NEWS_DIR, PDD_DIR, CHROMA_DIR, CHATS_DIR, LOGS_DIR]) {
  fs.mkdirSync(dirPath, { recursive: true });
}

export const COLLECTION_LAWS = 'legal_laws';
export const COLLECTION_COURT = 'court_cases';
export const COLLECTION_CARS = 'car_catalog';
export const COLLECTION_NEWS = 'auto_news';
export const COLLECTION_PDD = 'traffic_rules';

export const SEARCH_COLLECTIONS = [
  COLLECTION_LAWS,
  COLLECTION_COURT,
  COLLECTION_NEWS,
  COLLECTION_PDD,
];

export const GEMINI_API_KEY = (process.env.GEMINI_API_KEY || '').trim();
export const MODEL_NAME = (process.env.LLM_MODEL_NAME || 'gemini-4-hydrogen').trim();
export const BACKUP_MODEL_NAME = 'gemini-3.1-flash-lite';

export const TOP_K_RETRIEVAL = Number(process.env.TOP_K_RETRIEVAL || 20);
export const TOP_K_RERANK = Number(process.env.TOP_K_RERANK || 5);

export const PRIORITY_HIGH_BOOST = 1.35;
export const PRIORITY_MEDIUM_BOOST = 1.15;

// Supabase PostgreSQL configuration with Render PORT & Linux USER guards
export const DATABASE_URL = (process.env.DATABASE_URL || '').trim();
export const SUPABASE_HOST = (
  process.env.HOST ||
  process.env.SUPABASE_HOST ||
  process.env.PGHOST ||
  ''
).trim();

let rawDbPort = (
  process.env.DB_PORT ||
  process.env.SUPABASE_PORT ||
  process.env.PGPORT ||
  process.env.PORT ||
  '5432'
).trim();

if (['10000', '8501', '80', '443', '3000'].includes(rawDbPort)) {
  rawDbPort = SUPABASE_HOST.includes('pooler') ? '6543' : '5432';
}
const parsedDbPort = Number.parseInt(rawDbPort, 10);
export const SUPABASE_PORT = Number.isFinite(parsedDbPort)
  ? parsedDbPort
  : SUPABASE_HOST.includes('pooler')
    ? 6543
    : 5432;

let sysUser = (
  process.env.SUPABASE_USER ||
  process.env.DB_USER ||
  process.env.PGUSER ||
  ''
).trim();
if (!sysUser && SUPABASE_HOST) {
  const envUser = (process.env.USER || '').trim();
  if (envUser && !['root', 'appuser', 'nobody', 'render'].includes(envUser)) {
    sysUser = envUser;
  }
}
export const SUPABASE_USER = sysUser;
export const SUPABASE_PASSWORD = (
  process.env.PASSWORD ||
  process.env.SUPABASE_PASSWORD ||
  process.env.PGPASSWORD ||
  ''
).trim();
export const SUPABASE_DBNAME = (
  process.env.DB_NAME ||
  process.env.SUPABASE_DB ||
  process.env.PGDATABASE ||
  'postgres'
).trim();

// Backblaze B2 S3 storage
export const B2_ENDPOINT = (process.env.B2_ENDPOINT || '').trim();
export const B2_KEY_ID = (process.env.B2_KEY_ID || '').trim();
export const B2_APPLICATION_KEY = (process.env.B2_APPLICATION_KEY || '').trim();
export const B2_REGION = (process.env.B2_REGION || 'eu-central-003').trim();
export const B2_BUCKET_NAME = (process.env.B2_BUCKET_NAME || process.env.B2_BUCKET || '').trim();

// Render wake-up webhook URL
export const WEBHOOK_BASE_URL = (
  process.env.WEBHOOK_BASE_URL ||
  process.env.RENDER_EXTERNAL_URL ||
  process.env.APP_URL ||
  ''
)
  .trim()
  .replace(/\/+$/, '');

export const SERVER_PORT = Number(process.env.PORT || 3000);
