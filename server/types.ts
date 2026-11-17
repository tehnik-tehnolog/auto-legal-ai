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

export interface LegalChapterDoc {
  parent_id: string;
  doc_id?: string;
  code: string;
  section?: string;
  chapter_number?: string;
  chapter_title?: string;
  article_number?: string;
  article_title?: string;
  title: string;
  category?: string;
  original_url?: string;
  url?: string;
  priority_level?: string;
  details?: string;
  body: string;
  full_text?: string;
}

export interface PddChapterDoc {
  parent_id: string;
  doc_id?: string;
  section_number?: number;
  chapter_number?: string;
  chapter_title?: string;
  title: string;
  category?: string;
  source?: string;
  original_url?: string;
  url?: string;
  priority_level?: string;
  body: string;
  full_text?: string;
}

export interface KBStats {
  legal: number;
  civics: number;
  tax: number;
  pdd: number;
  court: number;
  news: number;
}
