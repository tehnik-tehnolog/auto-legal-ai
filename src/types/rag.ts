export type ThemeMode = 'light' | 'dark';

export type NavSection = 'chat' | 'legal' | 'pdd';

export type UiIconName =
  | 'add_file'
  | 'court'
  | 'pdd'
  | 'pin'
  | 'regulatory'
  | 'remove'
  | 'rename'
  | 'unpin';

export interface RAGSourceItem {
  citation_id: number;
  chunk_id: string;
  parent_id?: string;
  collection: string;
  title: string;
  url: string;
  doc_type?: string;
  case_number?: string;
  date?: string;
  similarity_score: number;
  matched_chunk: string;
  source_tag: 'standard_retrieval' | 'topic_expansion';
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: RAGSourceItem[];
  topics?: string[];
  targets?: string[];
  attached_filename?: string | null;
  attached_chars?: number;
  attached_b2_key?: string | null;
  attached_download_url?: string | null;
  fallback_used?: boolean;
  fallback_reason?: string | null;
  created_at?: string;
}

export interface ChatMeta {
  chat_id: string;
  title: string;
  created_at: string;
  pinned: boolean;
}

export interface UserProfileMeta {
  user_id: string;
  email: string;
  user_name: string;
  active_chat_id: string | null;
  chats: ChatMeta[];
}

export interface KBStats {
  legal: number;
  civics: number;
  tax: number;
  pdd: number;
  court: number;
  news: number;
}

export interface LegalSummaryItem {
  parent_id: string;
  doc_id?: string;
  code: string;
  chapter_number?: string;
  article_number?: string;
  title: string;
  category?: string;
  priority_level?: string;
}

export interface LegalChapterDoc extends LegalSummaryItem {
  section?: string;
  chapter_title?: string;
  article_title?: string;
  original_url?: string;
  url?: string;
  details?: string;
  body: string;
  full_text?: string;
}

export interface PddTocItem {
  parent_id: string;
  chapter_number?: string;
  chapter_title?: string;
  title: string;
}

export interface PddChapterDoc extends PddTocItem {
  doc_id?: string;
  section_number?: number;
  category?: string;
  source?: string;
  original_url?: string;
  url?: string;
  body: string;
  full_text?: string;
}

export interface ActiveJobState {
  jobId: string;
  chatId: string;
  status: 'started' | 'retrieving' | 'generating' | 'completed' | 'error';
  error?: string | null;
}
