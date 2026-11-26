import fs from 'node:fs';
import path from 'node:path';
import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  ListBucketsCommand,
  ListObjectsV2Command,
  type _Object,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import {
  B2_APPLICATION_KEY,
  B2_BUCKET_NAME,
  B2_ENDPOINT,
  B2_KEY_ID,
  B2_REGION,
  DATA_DIR,
} from './config';

const KB_SUBDIRS = ['legal', 'pdd', 'court', 'news', 'cars', 'chroma'];

export interface B2SyncStatus {
  configured: boolean;
  bucket: string | null;
  dataDir: string;
  prefixUsed: string | null;
  found: number;
  downloaded: number;
  skipped: number;
  errors: number;
  lastError: string | null;
  lastSyncAt: string | null;
}

function collectFilesRecursively(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'cache' || entry.name.startsWith('.')) continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectFilesRecursively(fullPath));
    } else if (entry.isFile()) {
      results.push(fullPath);
    }
  }
  return results;
}

function guessContentType(filePath: string): string {
  const lower = filePath.toLowerCase();
  if (lower.endsWith('.json') || lower.endsWith('.jsonl')) return 'application/json; charset=utf-8';
  if (lower.endsWith('.md')) return 'text/markdown; charset=utf-8';
  if (lower.endsWith('.txt')) return 'text/plain; charset=utf-8';
  if (lower.endsWith('.pdf')) return 'application/pdf';
  if (lower.endsWith('.sqlite3') || lower.endsWith('.bin')) return 'application/octet-stream';
  return 'application/octet-stream';
}

function normalizeKbRelativePath(rawKey: string): string {
  let rel = rawKey.replace(/^\/+/, '');
  if (rel.startsWith('kb/')) {
    rel = rel.slice('kb/'.length);
  } else if (rel.startsWith('data/')) {
    rel = rel.slice('data/'.length);
  }
  return rel.replace(/^\/+/, '');
}

class B2StorageService {
  private client: S3Client | null = null;
  private resolvedBucket: string | null = null;
  private lastSyncStatus: B2SyncStatus = {
    configured: false,
    bucket: null,
    dataDir: DATA_DIR,
    prefixUsed: null,
    found: 0,
    downloaded: 0,
    skipped: 0,
    errors: 0,
    lastError: null,
    lastSyncAt: null,
  };

  isConfigured(): boolean {
    return Boolean(B2_ENDPOINT && B2_KEY_ID && B2_APPLICATION_KEY);
  }

  getSyncStatus(): B2SyncStatus {
    return { ...this.lastSyncStatus, configured: this.isConfigured(), dataDir: DATA_DIR };
  }

  private getClient(): S3Client | null {
    if (!this.isConfigured()) return null;
    if (this.client) return this.client;

    this.client = new S3Client({
      endpoint: B2_ENDPOINT,
      region: B2_REGION || 'eu-central-003',
      credentials: {
        accessKeyId: B2_KEY_ID,
        secretAccessKey: B2_APPLICATION_KEY,
      },
      forcePathStyle: true,
      requestChecksumCalculation: 'WHEN_REQUIRED',
      responseChecksumValidation: 'WHEN_REQUIRED',
    });
    return this.client;
  }

  async getBucketName(): Promise<string | null> {
    if (B2_BUCKET_NAME) return B2_BUCKET_NAME;
    if (this.resolvedBucket) return this.resolvedBucket;
    const client = this.getClient();
    if (!client) return null;
    try {
      const resp = await client.send(new ListBucketsCommand({}));
      const first = resp.Buckets?.[0]?.Name;
      if (first) {
        this.resolvedBucket = first;
        return first;
      }
      this.lastSyncStatus.lastError = 'No buckets returned by Backblaze B2 ListBuckets.';
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      this.lastSyncStatus.lastError = `ListBuckets failed (${msg}). Set B2_BUCKET_NAME explicitly for bucket-restricted keys.`;
      console.warn(`[B2] Unable to list buckets (${msg}). Set B2_BUCKET_NAME explicitly if using a single-bucket key.`);
    }
    return null;
  }

  async uploadBytes(objectKey: string, data: Buffer, contentType?: string): Promise<string | null> {
    const client = this.getClient();
    const bucket = await this.getBucketName();
    if (!client || !bucket) return null;

    try {
      await client.send(
        new PutObjectCommand({
          Bucket: bucket,
          Key: objectKey,
          Body: data,
          ContentType: contentType || 'application/octet-stream',
        })
      );
      return objectKey;
    } catch (err) {
      console.error(`[B2] Failed to upload ${objectKey}:`, err);
      return null;
    }
  }

  async uploadUserAttachment(
    userEmail: string,
    chatId: string,
    filename: string,
    fileBytes: Buffer,
    mimeType?: string
  ): Promise<string | null> {
    const safeEmail = userEmail.toLowerCase().replace(/[^a-z0-9_.-]/g, '_');
    const safeChat = chatId.replace(/[^a-zA-Z0-9_-]/g, '_');
    const safeName = filename.replace(/[^a-zA-Zа-яА-ЯёЁ0-9_.-]/g, '_');
    const ts = new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 15);
    const key = `attachments/${safeEmail}/${safeChat}/${ts}_${safeName}`;
    return this.uploadBytes(key, fileBytes, mimeType);
  }

  async getPresignedUrl(objectKey: string, expiresIn = 3600): Promise<string | null> {
    const client = this.getClient();
    const bucket = await this.getBucketName();
    if (!client || !bucket || !objectKey) return null;
    try {
      const cmd = new GetObjectCommand({ Bucket: bucket, Key: objectKey });
      return await getSignedUrl(client, cmd, { expiresIn });
    } catch (err) {
      console.warn(`[B2] Presigned URL failed for ${objectKey}:`, err);
      return null;
    }
  }

  private async listObjectsByPrefix(
    client: S3Client,
    bucket: string,
    prefix: string
  ): Promise<_Object[]> {
    const items: _Object[] = [];
    let continuationToken: string | undefined;
    do {
      const listResp = await client.send(
        new ListObjectsV2Command({
          Bucket: bucket,
          Prefix: prefix,
          ContinuationToken: continuationToken,
        })
      );
      for (const obj of listResp.Contents || []) {
        items.push(obj);
      }
      continuationToken = listResp.NextContinuationToken;
    } while (continuationToken);
    return items;
  }

  async syncKbFromB2(
    targetDir = DATA_DIR
  ): Promise<{ configured: boolean; downloaded: number; skipped: number; errors: number }> {
    const summary = { configured: this.isConfigured(), downloaded: 0, skipped: 0, errors: 0 };
    this.lastSyncStatus = {
      configured: this.isConfigured(),
      bucket: B2_BUCKET_NAME || this.resolvedBucket,
      dataDir: targetDir,
      prefixUsed: null,
      found: 0,
      downloaded: 0,
      skipped: 0,
      errors: 0,
      lastError: null,
      lastSyncAt: new Date().toISOString(),
    };

    if (!this.isConfigured()) {
      this.lastSyncStatus.lastError = 'Backblaze B2 credentials are not configured.';
      return summary;
    }

    const client = this.getClient();
    const bucket = await this.getBucketName();
    if (!client || !bucket) {
      summary.errors += 1;
      this.lastSyncStatus.errors = summary.errors;
      return summary;
    }

    this.lastSyncStatus.bucket = bucket;
    console.log(
      `[B2] Syncing KB into "${targetDir}" from bucket "${bucket}" (endpoint=${B2_ENDPOINT}, region=${B2_REGION})...`
    );

    try {
      // Support multiple bucket layouts: kb/<sub/...>, data/<sub/...>, or root <sub/...>
      let objects: _Object[] = await this.listObjectsByPrefix(client, bucket, 'kb/');
      let prefixUsed = 'kb/';

      if (objects.length === 0) {
        const dataObjects = await this.listObjectsByPrefix(client, bucket, 'data/');
        if (dataObjects.length > 0) {
          objects = dataObjects;
          prefixUsed = 'data/';
        }
      }

      if (objects.length === 0) {
        const rootObjects: _Object[] = [];
        for (const sub of KB_SUBDIRS) {
          const subObjs = await this.listObjectsByPrefix(client, bucket, `${sub}/`);
          rootObjects.push(...subObjs);
        }
        if (rootObjects.length > 0) {
          objects = rootObjects;
          prefixUsed = 'root';
        }
      }

      this.lastSyncStatus.prefixUsed = prefixUsed;
      this.lastSyncStatus.found = objects.length;

      if (objects.length === 0) {
        const msg = `No KB objects found in bucket "${bucket}" under prefixes "kb/", "data/", or root (${KB_SUBDIRS.join(', ')}).`;
        console.warn(`[B2] ${msg}`);
        this.lastSyncStatus.lastError = msg;
        return summary;
      }

      for (const obj of objects) {
        const key = obj.Key;
        if (!key || key.endsWith('/')) continue;

        const relPath = normalizeKbRelativePath(key);
        if (!relPath) continue;
        // Skip cache directories and non-KB prefixes
        const topDir = relPath.split('/')[0];
        if (!KB_SUBDIRS.includes(topDir)) continue;
        if (relPath.includes('/cache/') || relPath.startsWith('cache/')) continue;

        const localPath = path.join(targetDir, relPath);
        if (fs.existsSync(localPath) && fs.statSync(localPath).size === obj.Size) {
          summary.skipped += 1;
          continue;
        }

        try {
          fs.mkdirSync(path.dirname(localPath), { recursive: true });
          const getResp = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
          if (getResp.Body) {
            const chunks: Buffer[] = [];
            for await (const chunk of getResp.Body as AsyncIterable<Uint8Array>) {
              chunks.push(Buffer.from(chunk));
            }
            fs.writeFileSync(localPath, Buffer.concat(chunks));
            summary.downloaded += 1;
          }
        } catch (fileErr) {
          summary.errors += 1;
          const msg = fileErr instanceof Error ? fileErr.message : String(fileErr);
          this.lastSyncStatus.lastError = `Failed downloading ${key}: ${msg}`;
          console.error(`[B2] Failed downloading ${key} -> ${localPath}:`, fileErr);
        }
      }

      this.lastSyncStatus.downloaded = summary.downloaded;
      this.lastSyncStatus.skipped = summary.skipped;
      this.lastSyncStatus.errors = summary.errors;
      console.log(
        `[B2] Sync complete (prefix="${prefixUsed}", found=${objects.length}, downloaded=${summary.downloaded}, skipped=${summary.skipped}, errors=${summary.errors}).`
      );
    } catch (err) {
      summary.errors += 1;
      const msg = err instanceof Error ? err.message : String(err);
      this.lastSyncStatus.errors = summary.errors;
      this.lastSyncStatus.lastError = msg;
      console.error('[B2] KB sync failed:', err);
    }
    return summary;
  }

  async uploadKbToB2(
    sourceDir = DATA_DIR
  ): Promise<{ configured: boolean; uploaded: number; skipped: number; errors: number }> {
    const summary = { configured: this.isConfigured(), uploaded: 0, skipped: 0, errors: 0 };
    if (!this.isConfigured()) return summary;

    const client = this.getClient();
    const bucket = await this.getBucketName();
    if (!client || !bucket) return summary;

    // Fetch existing sizes in kb/ to avoid redundant uploads
    const remoteSizes = new Map<string, number>();
    try {
      const existing = await this.listObjectsByPrefix(client, bucket, 'kb/');
      for (const obj of existing) {
        if (obj.Key && typeof obj.Size === 'number') {
          remoteSizes.set(obj.Key, obj.Size);
        }
      }
    } catch (err) {
      console.warn('[B2] Unable to inspect remote kb/ objects:', err);
    }

    for (const sub of KB_SUBDIRS) {
      const subDir = path.join(sourceDir, sub);
      const files = collectFilesRecursively(subDir);
      for (const filePath of files) {
        const rel = path.relative(sourceDir, filePath).split(path.sep).join('/');
        const b2Key = `kb/${rel}`;
        const stat = fs.statSync(filePath);
        if (remoteSizes.get(b2Key) === stat.size) {
          summary.skipped += 1;
          continue;
        }
        try {
          const data = fs.readFileSync(filePath);
          await client.send(
            new PutObjectCommand({
              Bucket: bucket,
              Key: b2Key,
              Body: data,
              ContentType: guessContentType(filePath),
            })
          );
          summary.uploaded += 1;
          console.log(`[B2] Uploaded ${b2Key} (${stat.size} bytes)`);
        } catch (err) {
          console.error(`[B2] Failed to upload ${b2Key}:`, err);
          summary.errors += 1;
        }
      }
    }

    return summary;
  }
}

export const b2Storage = new B2StorageService();
