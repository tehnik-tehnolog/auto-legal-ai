import { b2Storage } from './b2Storage';
import { DATA_DIR } from './config';

async function main() {
  const args = new Set(process.argv.slice(2));
  if (!b2Storage.isConfigured()) {
    console.error(
      '[B2] Backblaze B2 не настроен. Проверьте переменные окружения: B2_ENDPOINT, B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME.'
    );
    process.exit(1);
  }

  if (args.has('--upload')) {
    console.log(`[B2] Загрузка базы знаний из ${DATA_DIR} в бакет Backblaze B2 (kb/)...`);
    const res = await b2Storage.uploadKbToB2(DATA_DIR);
    console.log('[B2] Готово:', res);
    return;
  }

  if (args.has('--sync')) {
    console.log(`[B2] Синхронизация базы знаний из Backblaze B2 (kb/) в ${DATA_DIR}...`);
    const res = await b2Storage.syncKbFromB2(DATA_DIR);
    console.log('[B2] Готово:', res);
    return;
  }

  const bucket = await b2Storage.getBucketName();
  console.log({ configured: b2Storage.isConfigured(), bucket });
}

main().catch((err) => {
  console.error('[B2] Fatal error:', err);
  process.exit(1);
});
