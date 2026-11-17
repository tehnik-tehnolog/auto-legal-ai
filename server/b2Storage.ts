import fs from 'node:fs';
import path from 'node:path';
import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  ListBucketsCommand,
  ListObjectsV2Command,
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

class B2StorageService {
  private client: S3Client | null = null;
  private resolvedBucket: string | null = null;

  isConfigured(): boolean {
    return Boolean(B2_ENDPOINT && B2_KEY_ID && B2_APPLICATION_KEY);
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
    } catch (err) {
      console.warn('[B2] Unable to list buckets:', err);
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

  async syncKbFromB2(targetDir = DATA_DIR): Promise<{ configured: boolean; downloaded: number; skipped: number }> {
    const summary = { configured: this.isConfigured(), downloaded: 0, skipped: 0 };
    if (!this.isConfigured()) return summary;

    const client = this.getClient();
    const bucket = await this.getBucketName();
    if (!client || !bucket) return summary;

    try {
      let continuationToken: string | undefined;
      do {
        const listResp = await client.send(
          new ListObjectsV2Command({
            Bucket: bucket,
            Prefix: 'kb/',
            ContinuationToken: continuationToken,
          })
        );

        for (const obj of listResp.Contents || []) {
          const key = obj.Key;
          if (!key) continue;
          const relPath = key.replace(/^kb\//, '').replace(/^\/+/, '');
          if (!relPath || relPath.endsWith('/')) continue;

          const localPath = path.join(targetDir, relPath);
          if (fs.existsSync(localPath) && fs.statSync(localPath).size === obj.Size) {
            summary.skipped += 1;
            continue;
          }

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
        }
        continuationToken = listResp.NextContinuationToken;
      } while (continuationToken);
    } catch (err) {
      console.warn('[B2] KB sync warning:', err);
    }
    return summary;
  }
}

export const b2Storage = new B2StorageService();
