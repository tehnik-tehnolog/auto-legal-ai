import fs from 'node:fs';
import path from 'node:path';
import { GoogleGenAI, Type } from '@google/genai';
import {
  BACKUP_MODEL_NAME,
  CHROMA_DIR,
  COLLECTION_COURT,
  COLLECTION_LAWS,
  COLLECTION_NEWS,
  COLLECTION_PDD,
  GEMINI_API_KEY,
  LEGAL_CHAPTERS_FILE,
  LEGAL_JSONL_FILE,
  LOGS_DIR,
  MODEL_NAME,
  PDD_CHAPTERS_FILE,
  PRIORITY_HIGH_BOOST,
  PRIORITY_MEDIUM_BOOST,
  SEARCH_COLLECTIONS,
  TOP_K_RERANK,
  TOP_K_RETRIEVAL,
} from './config';
import { tokenizeAndStem } from './russianStemmer';
import type { KBStats, LegalChapterDoc, PddChapterDoc, RAGSourceItem } from './types';

export const SYSTEM_PROMPT = `Ты — юридический RAG ассистент компании, специализирующейся на аренде автомобилей с последующим выкупом (раскате) в Российской Федерации.

Твоя задача — проанализировать вопрос юриста компании и предоставленные фрагменты кодексов (ГК, НК, КоАП) вместе со ссылками на них. И дать ответ.

Правила работы с контекстом и источниками:
0. Без приветствий и прелюдий переходи сразу к ответу на вопрос.
1. Если переданные статьи и ссылки релевантны вопросу, активно используй их в тексте ответа, ссылаясь на конкретные нормы. [Название статьи/закона](URL_ИЗ_БЛОКА_ИСТОЧНИКА).
2. Если предоставленный контекст нерелевантен или его недостаточно, опирайся на свои глубокие знания законодательства РФ. Ссылайся на актуальные нормы права, учитывая практику и официальные источники (приоритетно на портал docs.cntd.ru). [Об обязательном страховании гражданской ответственности владельцев транспортных средств](https://docs.cntd.ru/document/901817083).
3. Всегда адаптируй ответ под специфику бизнеса компании (раскат, аренда транспортных средств с выкупом, учет на балансе, риски и налоговые последствия) в правовом поле РФ(важно).
4. Оформляй итоговый ответ в структурированном виде с использованием разметки Markdown.`;

const PDD_KEYWORDS = [
  'пдд',
  'правил дорожн',
  'скорост',
  'обгон',
  'знак',
  'разметк',
  'пешеход',
  'дтп',
  'светофор',
  'лишени прав',
  'помех справ',
  'детск кресл',
  'неисправност',
  'тормоз',
  'европротокол',
  'фары',
  'техосмотр',
];

const NEWS_KEYWORDS = [
  'новост',
  'утильсбор',
  'рынок',
  'динамик',
  'тенденци',
  'индексац',
  'автопром',
  'прогноз продаж',
];

interface RawChunk {
  id: string;
  parent_id?: string;
  text: string;
  metadata?: Record<string, string>;
}

interface ParentDoc {
  parent_id?: string;
  title?: string;
  url?: string;
  original_url?: string;
  date?: string;
  case_number?: string;
  full_text?: string;
}

class SimpleBM25Index {
  private docIds: string[] = [];
  private docsMap = new Map<string, RawChunk>();
  private tokenMaps: Map<string, number>[] = [];
  private docLens: number[] = [];
  private avgdl = 1;
  private idf = new Map<string, number>();

  build(chunks: RawChunk[]): void {
    this.docIds = [];
    this.docsMap.clear();
    this.tokenMaps = [];
    this.docLens = [];
    this.idf.clear();

    const docFreq = new Map<string, number>();
    let totalLen = 0;

    for (const chunk of chunks) {
      this.docIds.push(chunk.id);
      this.docsMap.set(chunk.id, chunk);
      const stems = tokenizeAndStem(chunk.text);
      const tfMap = new Map<string, number>();
      for (const s of stems) {
        tfMap.set(s, (tfMap.get(s) || 0) + 1);
      }
      for (const uniqueStem of tfMap.keys()) {
        docFreq.set(uniqueStem, (docFreq.get(uniqueStem) || 0) + 1);
      }
      this.tokenMaps.push(tfMap);
      this.docLens.push(stems.length);
      totalLen += stems.length;
    }

    const nDocs = chunks.length;
    this.avgdl = nDocs > 0 ? totalLen / nDocs : 1;
    for (const [stem, freq] of docFreq.entries()) {
      this.idf.set(stem, Math.log(1 + (nDocs - freq + 0.5) / (freq + 0.5)));
    }
  }

  getChunk(id: string): RawChunk | undefined {
    return this.docsMap.get(id);
  }

  search(query: string, topK = 20, k1 = 1.5, b = 0.75): Array<{ id: string; score: number }> {
    const qStems = tokenizeAndStem(query);
    if (qStems.length === 0 || this.docIds.length === 0) return [];

    const scored: Array<{ id: string; score: number }> = [];
    for (let i = 0; i < this.docIds.length; i++) {
      const tfMap = this.tokenMaps[i];
      const docLen = this.docLens[i];
      let score = 0;

      for (const q of qStems) {
        const f = tfMap.get(q);
        if (f) {
          const idfVal = this.idf.get(q) ?? 0.5;
          const num = f * (k1 + 1);
          const denom = f + k1 * (1 - b + b * (docLen / (this.avgdl || 1)));
          score += idfVal * (num / denom);
        }
      }

      if (score > 0) {
        scored.push({ id: this.docIds[i], score });
      }
    }

    scored.sort((a, bItem) => bItem.score - a.score);
    return scored.slice(0, topK);
  }
}

interface CandidateItem {
  id: string;
  collection: string;
  text: string;
  metadata: Record<string, string>;
  rrf_score: number;
  rerank_score?: number;
}

function logGeminiError(eventType: string, query: string, reason: string): void {
  try {
    const logPath = path.join(LOGS_DIR, 'gemini_connection.log');
    const ts = new Date().toISOString().replace('T', ' ').slice(0, 19);
    const entry = `\n${'='.repeat(70)}\n[${ts}] [EVENT: ${eventType}]\nВопрос: ${query}\nПричина: ${reason}\nМодель: ${MODEL_NAME}\n${'='.repeat(70)}\n`;
    fs.appendFileSync(logPath, entry, 'utf-8');
  } catch {
    // ignore log write failures on read-only systems
  }
}

class RAGEngineService {
  private initialized = false;
  private legalDocs: LegalChapterDoc[] = [];
  private pddDocs: PddChapterDoc[] = [];
  private parentStore: Record<string, ParentDoc> = {};
  private bm25Map = new Map<string, SimpleBM25Index>();
  private collectionCounts: Record<string, number> = {};

  ensureLoaded(): void {
    if (this.initialized) return;
    this.reload();
  }

  reload(): void {
    this.legalDocs = [];
    const legalPath = fs.existsSync(LEGAL_CHAPTERS_FILE) ? LEGAL_CHAPTERS_FILE : LEGAL_JSONL_FILE;
    if (fs.existsSync(legalPath)) {
      const lines = fs.readFileSync(legalPath, 'utf-8').split(/\r?\n/);
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed) {
          try {
            this.legalDocs.push(JSON.parse(trimmed) as LegalChapterDoc);
          } catch {
            // skip malformed line
          }
        }
      }
    }

    this.pddDocs = [];
    if (fs.existsSync(PDD_CHAPTERS_FILE)) {
      const lines = fs.readFileSync(PDD_CHAPTERS_FILE, 'utf-8').split(/\r?\n/);
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed) {
          try {
            this.pddDocs.push(JSON.parse(trimmed) as PddChapterDoc);
          } catch {
            // skip malformed line
          }
        }
      }
    }

    const parentPath = path.join(CHROMA_DIR, 'parent_store.json');
    if (fs.existsSync(parentPath)) {
      try {
        this.parentStore = JSON.parse(fs.readFileSync(parentPath, 'utf-8')) as Record<string, ParentDoc>;
      } catch {
        this.parentStore = {};
      }
    }

    this.bm25Map.clear();
    this.collectionCounts = {};
    for (const coll of SEARCH_COLLECTIONS) {
      const chunksPath = path.join(CHROMA_DIR, `${coll}_chunks.json`);
      if (fs.existsSync(chunksPath)) {
        try {
          const chunks = JSON.parse(fs.readFileSync(chunksPath, 'utf-8')) as RawChunk[];
          const idx = new SimpleBM25Index();
          idx.build(chunks);
          this.bm25Map.set(coll, idx);
          this.collectionCounts[coll] = chunks.length;
        } catch {
          this.collectionCounts[coll] = 0;
        }
      }
    }

    this.initialized = true;
    console.log(
      `[RAG] Loaded ${this.legalDocs.length} legal articles, ${this.pddDocs.length} PDD chapters, collections:`,
      this.collectionCounts
    );
  }

  getStats(): KBStats {
    this.ensureLoaded();
    const tax = this.legalDocs.filter(
      (d) => (d.code || '').includes('НК') || (d.parent_id || '').includes('tax')
    ).length;
    const civics = this.legalDocs.filter(
      (d) => (d.code || '').includes('ГК') || (d.parent_id || '').includes('civics')
    ).length;

    return {
      legal: this.legalDocs.length,
      civics,
      tax,
      pdd: this.pddDocs.length,
      court: this.collectionCounts[COLLECTION_COURT] || 0,
      news: this.collectionCounts[COLLECTION_NEWS] || 0,
    };
  }

  getLegalDocs(): LegalChapterDoc[] {
    this.ensureLoaded();
    return this.legalDocs;
  }

  getPddDocs(): PddChapterDoc[] {
    this.ensureLoaded();
    return this.pddDocs;
  }

  private createGeminiClient(): GoogleGenAI | null {
    const key = GEMINI_API_KEY || (process.env.GEMINI_API_KEY || '').trim();
    if (!key) return null;
    return new GoogleGenAI({
      apiKey: key,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    });
  }

  private routeCollections(query: string): string[] {
    const q = query.toLowerCase();
    if (PDD_KEYWORDS.some((k) => q.includes(k))) {
      return [COLLECTION_PDD, COLLECTION_LAWS];
    }
    if (NEWS_KEYWORDS.some((k) => q.includes(k))) {
      return [COLLECTION_NEWS, COLLECTION_LAWS];
    }
    return [COLLECTION_LAWS, COLLECTION_COURT];
  }

  private rerankCandidates(query: string, candidates: CandidateItem[]): CandidateItem[] {
    const qLower = query.toLowerCase();
    const qStems = new Set(tokenizeAndStem(query));
    const articleNums = new Set(qLower.match(/\b\d{1,4}(?:[._]\d+)?\b/g) || []);
    const wantsArticles = ['стать', 'ст.', 'гк рф', 'нк рф', 'кодекс'].some((k) =>
      qLower.includes(k)
    );

    for (const item of candidates) {
      const fullText = `${item.text} ${item.metadata?.title || ''}`;
      const docStems = new Set(tokenizeAndStem(fullText));
      let overlap = 0;
      for (const s of qStems) {
        if (docStems.has(s)) overlap += 1;
      }
      const lexicalMultiplier = 1.0 + Math.min(overlap, 10) * 0.08;

      let articleMultiplier = 1.0;
      if (articleNums.size > 0) {
        const tLower = item.text.toLowerCase();
        for (const num of articleNums) {
          const cleanNum = num.replace(/[_-]/g, '.');
          if (
            tLower.includes(`статья ${num}`) ||
            tLower.includes(`ст. ${num}`) ||
            tLower.includes(`статье ${num}`) ||
            tLower.includes(`статья ${cleanNum}`)
          ) {
            articleMultiplier += 0.35;
          }
        }
      }

      const normMultiplier = item.collection === COLLECTION_LAWS && wantsArticles ? 1.25 : 1.0;
      const priority = item.metadata?.priority_level || 'standard';
      const boost =
        priority === 'high'
          ? PRIORITY_HIGH_BOOST
          : priority === 'medium'
            ? PRIORITY_MEDIUM_BOOST
            : 1.0;

      const baseScore = item.rrf_score || 0.02;
      item.rerank_score = Number(
        (baseScore * boost * lexicalMultiplier * articleMultiplier * normMultiplier).toFixed(4)
      );
    }

    return [...candidates].sort((a, b) => (b.rerank_score || 0) - (a.rerank_score || 0));
  }

  private stratifiedSelection(
    query: string,
    ranked: CandidateItem[],
    topK = TOP_K_RERANK
  ): CandidateItem[] {
    const q = query.toLowerCase();
    const hasPdd = PDD_KEYWORDS.some((k) => q.includes(k));
    const hasNews = NEWS_KEYWORDS.some((k) => q.includes(k));

    const quotas: Array<[string, number]> = hasPdd
      ? [
          [COLLECTION_PDD, 3],
          [COLLECTION_LAWS, 2],
        ]
      : hasNews
        ? [
            [COLLECTION_NEWS, 2],
            [COLLECTION_LAWS, 3],
          ]
        : [
            [COLLECTION_LAWS, 4],
            [COLLECTION_COURT, 1],
          ];

    const byColl = new Map<string, CandidateItem[]>();
    for (const item of ranked) {
      const list = byColl.get(item.collection) || [];
      list.push(item);
      byColl.set(item.collection, list);
    }

    const selected: CandidateItem[] = [];
    const selectedIds = new Set<string>();

    for (const [coll, count] of quotas) {
      const items = byColl.get(coll) || [];
      let picked = 0;
      const seenParents = new Set<string>();

      for (const item of items) {
        const pId = item.metadata?.parent_id || item.id;
        if (!selectedIds.has(item.id) && !seenParents.has(pId)) {
          selected.push(item);
          selectedIds.add(item.id);
          seenParents.add(pId);
          picked += 1;
          if (picked >= count) break;
        }
      }

      if (picked < count) {
        for (const item of items) {
          if (!selectedIds.has(item.id)) {
            selected.push(item);
            selectedIds.add(item.id);
            picked += 1;
            if (picked >= count) break;
          }
        }
      }
    }

    if (selected.length < topK) {
      for (const item of ranked) {
        if (selected.length >= topK) break;
        if (!selectedIds.has(item.id)) {
          selected.push(item);
          selectedIds.add(item.id);
        }
      }
    }

    return selected.slice(0, topK);
  }

  private retrieveStandard(query: string): {
    targetCollections: string[];
    sources: RAGSourceItem[];
  } {
    const targetCollections = this.routeCollections(query);
    const candidates: CandidateItem[] = [];

    for (const coll of targetCollections) {
      const idx = this.bm25Map.get(coll);
      if (!idx) continue;
      const hits = idx.search(query, TOP_K_RETRIEVAL);
      hits.forEach((hit, rank) => {
        const chunk = idx.getChunk(hit.id);
        if (chunk) {
          candidates.push({
            id: chunk.id,
            collection: coll,
            text: chunk.text,
            metadata: chunk.metadata || {},
            rrf_score: 1.0 / (60.0 + rank),
          });
        }
      });
    }

    if (candidates.length === 0) {
      return { targetCollections, sources: [] };
    }

    const ranked = this.rerankCandidates(query, candidates);
    const top5 = this.stratifiedSelection(query, ranked, 5);

    const sources: RAGSourceItem[] = top5.map((item, idx) => {
      const meta = item.metadata || {};
      const parentId = meta.parent_id;
      const parentDoc = parentId ? this.parentStore[parentId] || {} : {};
      const cleanPid = parentId || item.id;
      let url = parentDoc.url || meta.url || '#';
      if (item.collection === COLLECTION_LAWS && cleanPid) {
        url = `?doc=${cleanPid}#doc-legal_${cleanPid}`;
      } else if (item.collection === COLLECTION_PDD && cleanPid) {
        url = `?pdd=${cleanPid}#doc-pdd_${cleanPid}`;
      }

      return {
        citation_id: idx + 1,
        chunk_id: item.id,
        parent_id: parentId,
        collection: item.collection,
        title: parentDoc.title || meta.title || 'Документ',
        url,
        doc_type: meta.doc_type || 'document',
        case_number: parentDoc.case_number || meta.case_number || '',
        date: parentDoc.date || meta.date || '',
        similarity_score: item.rerank_score || 0,
        matched_chunk: item.text,
        source_tag: 'standard_retrieval',
      };
    });

    return { targetCollections, sources };
  }

  private async extractTopics(
    query: string,
    ai: GoogleGenAI | null
  ): Promise<{ topics: string[]; geminiConnected: boolean; error?: string }> {
    if (!ai) {
      return {
        topics: [],
        geminiConnected: false,
        error: 'GEMINI_API_KEY не задан в переменных окружения',
      };
    }

    const topicPrompt = `Ты — ведущий юрисконсульт по российскому законодательству. Проанализируй юридический вопрос юриста компании по аренде и выкупу авто (раскату):
"${query}"

Сформулируй от 2 до 6 конкретных поисковых тем/подзапросов для поиска релевантных статей в Гражданском кодексе РФ, Налоговом кодексе РФ, КоАП РФ, 164-ФЗ 'О лизинге', 40-ФЗ 'Об ОСАГО' и ПДД РФ. Каждая тема должна содержать 2-4 ключевых слова в именительном падеже.`;

    const modelsToTry = [MODEL_NAME, BACKUP_MODEL_NAME];
    let lastError = '';

    for (const modelId of modelsToTry) {
      try {
        const res = await ai.models.generateContent({
          model: modelId,
          contents: topicPrompt,
          config: {
            responseMimeType: 'application/json',
            responseSchema: {
              type: Type.ARRAY,
              items: { type: Type.STRING },
            },
          },
        });
        const rawText = (res.text || '').trim();
        const parsed = JSON.parse(rawText);
        if (Array.isArray(parsed)) {
          const cleaned = parsed
            .map((t) => String(t).trim())
            .filter(Boolean)
            .slice(0, 6);
          if (cleaned.length >= 2) {
            return { topics: cleaned, geminiConnected: true };
          }
        }
        return { topics: [], geminiConnected: true };
      } catch (err) {
        lastError = err instanceof Error ? err.message : String(err);
      }
    }

    logGeminiError('TOPIC_EXTRACTION_FAILED', query, lastError);
    return { topics: [], geminiConnected: false, error: lastError };
  }

  private expandTopics(
    query: string,
    topics: string[],
    standardSources: RAGSourceItem[]
  ): RAGSourceItem[] {
    if (topics.length === 0) return [];

    const candidatesMap = new Map<string, CandidateItem>();
    const targetColls = [COLLECTION_LAWS, COLLECTION_COURT, COLLECTION_PDD];

    for (const topic of topics) {
      for (const coll of targetColls) {
        const idx = this.bm25Map.get(coll);
        if (!idx) continue;
        const hits = idx.search(topic, 6);
        hits.forEach((hit, rank) => {
          const chunk = idx.getChunk(hit.id);
          if (chunk && !candidatesMap.has(chunk.id)) {
            candidatesMap.set(chunk.id, {
              id: chunk.id,
              collection: coll,
              text: chunk.text,
              metadata: chunk.metadata || {},
              rrf_score: 1.0 / (60.0 + rank),
            });
          }
        });
      }
    }

    const ranked = this.rerankCandidates(query, Array.from(candidatesMap.values()));
    const seenParents = new Set(standardSources.map((s) => s.parent_id).filter(Boolean) as string[]);
    const seenChunks = new Set(standardSources.map((s) => s.chunk_id));
    const topicSources: RAGSourceItem[] = [];

    for (const item of ranked) {
      if (topicSources.length >= 5) break;
      const pId = item.metadata?.parent_id;
      if (pId && seenParents.has(pId)) continue;
      if (seenChunks.has(item.id)) continue;

      const parentDoc = pId ? this.parentStore[pId] || {} : {};
      const cleanPid = pId || item.id;
      let url = parentDoc.url || item.metadata?.url || '#';
      if (item.collection === COLLECTION_LAWS && cleanPid) {
        url = `?doc=${cleanPid}#doc-legal_${cleanPid}`;
      } else if (item.collection === COLLECTION_PDD && cleanPid) {
        url = `?pdd=${cleanPid}#doc-pdd_${cleanPid}`;
      }

      topicSources.push({
        citation_id: standardSources.length + topicSources.length + 1,
        chunk_id: item.id,
        parent_id: pId,
        collection: item.collection,
        title: parentDoc.title || item.metadata?.title || 'Документ',
        url,
        doc_type: item.metadata?.doc_type || 'legal_law',
        case_number: parentDoc.case_number || item.metadata?.case_number || '',
        date: parentDoc.date || item.metadata?.date || '',
        similarity_score: item.rerank_score || 0,
        matched_chunk: item.text,
        source_tag: 'topic_expansion',
      });
      if (pId) seenParents.add(pId);
      seenChunks.add(item.id);
    }

    if (topicSources.length < 5) {
      for (const item of ranked) {
        if (topicSources.length >= 5) break;
        if (seenChunks.has(item.id)) continue;
        const pId = item.metadata?.parent_id;
        const parentDoc = pId ? this.parentStore[pId] || {} : {};
        const cleanPid = pId || item.id;
        let url = parentDoc.url || item.metadata?.url || '#';
        if (item.collection === COLLECTION_LAWS && cleanPid) {
          url = `?doc=${cleanPid}#doc-legal_${cleanPid}`;
        } else if (item.collection === COLLECTION_PDD && cleanPid) {
          url = `?pdd=${cleanPid}#doc-pdd_${cleanPid}`;
        }
        topicSources.push({
          citation_id: standardSources.length + topicSources.length + 1,
          chunk_id: item.id,
          parent_id: pId,
          collection: item.collection,
          title: parentDoc.title || item.metadata?.title || 'Документ',
          url,
          doc_type: item.metadata?.doc_type || 'legal_law',
          case_number: parentDoc.case_number || item.metadata?.case_number || '',
          date: parentDoc.date || item.metadata?.date || '',
          similarity_score: item.rerank_score || 0,
          matched_chunk: item.text,
          source_tag: 'topic_expansion',
        });
        seenChunks.add(item.id);
      }
    }

    return topicSources;
  }

  private extractiveFallback(sources: RAGSourceItem[], reason: string): string {
    const parts: string[] = [
      '**Ответ RAG-ассистента по базе знаний компании (сформирован локально по 5 базовым первоисточникам):**\n',
    ];

    if (reason) {
      parts.push(`> Причина переключения на локальный режим: ${reason}\n`);
    }

    const laws = sources.filter((s) => s.collection === COLLECTION_LAWS);
    const pdd = sources.filter((s) => s.collection === COLLECTION_PDD);
    const court = sources.filter((s) => s.collection === COLLECTION_COURT);
    const news = sources.filter((s) => s.collection === COLLECTION_NEWS);

    if (laws.length > 0) {
      parts.push('### Нормативно-правовое основание (ГК / НК / КоАП РФ)');
      for (const s of laws.slice(0, 5)) {
        parts.push(`- По нормам **[${s.title}](${s.url})**: ${s.matched_chunk.slice(0, 320)}...`);
      }
    }
    if (pdd.length > 0) {
      parts.push('### Правила дорожного движения РФ (ПДД РФ)');
      for (const s of pdd.slice(0, 3)) {
        parts.push(`- По правилам **[${s.title}](${s.url})**: ${s.matched_chunk.slice(0, 340)}...`);
      }
    }
    if (court.length > 0) {
      parts.push('### Позиция Верховного Суда РФ');
      for (const s of court.slice(0, 2)) {
        const caseNo = s.case_number || 'не указан';
        parts.push(
          `- В постановлении **[${s.title}](${s.url})** (Дело № ${caseNo}): ${s.matched_chunk.slice(0, 340)}...`
        );
      }
    }
    if (news.length > 0) {
      parts.push('### Рыночный контекст и аналитика');
      for (const s of news.slice(0, 2)) {
        parts.push(`- По данным **[${s.title}](${s.url})**: ${s.matched_chunk.slice(0, 260)}...`);
      }
    }

    return parts.join('\n\n');
  }

  async answerQuery(
    query: string,
    attachedDocText = '',
    onStage?: (stage: 'retrieving' | 'generating') => void
  ): Promise<{
    answer: string;
    sources: RAGSourceItem[];
    topics: string[];
    targets: string[];
    fallback_used: boolean;
    fallback_reason: string | null;
  }> {
    this.ensureLoaded();
    onStage?.('retrieving');

    const { targetCollections, sources: standardSources } = this.retrieveStandard(query);
    const ai = this.createGeminiClient();

    const topicRes = await this.extractTopics(query, ai);
    let topics = topicRes.topics;
    let finalSources: RAGSourceItem[] = standardSources;

    if (topicRes.geminiConnected && topics.length > 0) {
      const topicSources = this.expandTopics(query, topics, standardSources);
      finalSources = [...standardSources, ...topicSources].map((s, idx) => ({
        ...s,
        citation_id: idx + 1,
      }));
    }

    onStage?.('generating');

    const contextBlocks = finalSources.map((s) => {
      const tagLabel =
        s.source_tag === 'standard_retrieval' ? 'Базовый поиск' : 'Тематическое расширение';
      let block = `[Источник #${s.citation_id}] (${s.collection} | ${tagLabel})\nЗаголовок: ${s.title}\nСсылка: ${s.url}\n`;
      if (s.case_number) {
        block += `Номер дела: ${s.case_number} (Дата: ${s.date || 'н/д'})\n`;
      }
      block += `Текст нормы / фрагмента:\n${s.matched_chunk}\n`;
      return block;
    });

    let userPrompt = `КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ КОМПАНИИ (${finalSources.length} ПРОВЕРЕННЫХ ПЕРВОИСТОЧНИКОВ):\n${contextBlocks.join('\n---\n')}\n`;

    if (attachedDocText.trim()) {
      userPrompt += `\n---\n[ПРИКРЕПЛЕННЫЙ ДОКУМЕНТ ЮРИСТА ДЛЯ АНАЛИЗА]:\n${attachedDocText.trim().slice(0, 6000)}\n`;
    }

    userPrompt += `\n---\nВОПРОС ЮРИСТА:\n${query}\n\nДай структурированный, исчерпывающий ответ на русском языке со ссылками на первоисточники в формате Markdown.`;

    let answerText = '';
    let fallbackReason: string | null = topicRes.error || null;

    if (ai && topicRes.geminiConnected) {
      for (const modelId of [MODEL_NAME, BACKUP_MODEL_NAME]) {
        try {
          const response = await ai.models.generateContent({
            model: modelId,
            contents: userPrompt,
            config: {
              systemInstruction: SYSTEM_PROMPT,
            },
          });
          if (response.text && response.text.trim()) {
            answerText = response.text.trim();
            fallbackReason = null;
            break;
          }
        } catch (err) {
          fallbackReason = err instanceof Error ? err.message : String(err);
        }
      }
    }

    if (!answerText) {
      const reason =
        fallbackReason || 'GEMINI_API_KEY не задан или сервис Gemini временно недоступен';
      logGeminiError('FALLBACK_ACTIVATED', query, reason);
      // Strictly limit to 5 standard fragments when Gemini API connection fails
      const strict5 = standardSources.slice(0, 5);
      topics = [];
      return {
        answer: this.extractiveFallback(strict5, reason),
        sources: strict5,
        topics: [],
        targets: targetCollections,
        fallback_used: true,
        fallback_reason: reason,
      };
    }

    return {
      answer: answerText,
      sources: finalSources,
      topics,
      targets: targetCollections,
      fallback_used: false,
      fallback_reason: null,
    };
  }
}

export const ragEngine = new RAGEngineService();
