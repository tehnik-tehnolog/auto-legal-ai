import JSZip from 'jszip';
import { PDFParse } from 'pdf-parse';

function decodeXmlEntities(str: string): string {
  return str
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'");
}

export async function extractTextFromFile(buffer: Buffer, filename: string): Promise<string> {
  const lower = filename.toLowerCase();

  try {
    if (lower.endsWith('.pdf')) {
      const parser = new PDFParse({ data: new Uint8Array(buffer) });
      try {
        const res = await parser.getText();
        return (res.text || '').trim();
      } finally {
        await parser.destroy().catch(() => {});
      }
    }

    if (lower.endsWith('.docx')) {
      const zip = await JSZip.loadAsync(buffer);
      const docXmlFile = zip.file('word/document.xml');
      if (!docXmlFile) {
        return `[Файл ${filename} не содержит word/document.xml]`;
      }
      const xml = await docXmlFile.async('string');
      const paragraphs: string[] = [];
      const pMatches = xml.match(/<w:p[\s>][\s\S]*?<\/w:p>/g) || [];
      for (const pXml of pMatches) {
        const texts = Array.from(pXml.matchAll(/<w:t[^>]*>([\s\S]*?)<\/w:t>/g)).map((m) =>
          decodeXmlEntities(m[1])
        );
        const line = texts.join('').trim();
        if (line) {
          paragraphs.push(line);
        }
      }
      return paragraphs.join('\n\n');
    }

    return buffer.toString('utf-8').trim();
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return `[Ошибка извлечения текста из файла ${filename}: ${msg}]`;
  }
}
