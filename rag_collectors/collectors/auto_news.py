import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Set

import requests
from bs4 import BeautifulSoup

from collectors.base import BaseCollector
from config.settings import HTTP_TIMEOUT, NEWS_DIR, NEWSDATA_API_KEY, USER_AGENT

QUERIES = [
    '"утильсбор"',
    '"лизинг"',
    '"аренда авто"',
    '"с выкупом"',
    '"авторынок"',
    '"раскат"',
    '"вторичный рынок"',
    '"авто с пробегом"',
    '"автокредит"',
    '"ОСАГО"',
    '"цены на автомобили"',
    '"автопром"'
]

STOP_WORDS = [
    "самолет", "фильм", "новостройк", "квартир", "недвижимост",
    "убийств", "взятк", "стрельб", "охот"
]

FALLBACK_RSS_FEEDS = [
    "https://motor.ru/exports/rss",
    "https://www.autonews.ru/export/rss"
]


def clean_mojibake(text: str) -> str:
    """Очистка поврежденной кодировки"""
    if not text:
        return ""
    if "Ð" in text or "Ñ" in text or "Â" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except Exception:
            return ""
    return text


class AutoNewsCollector(BaseCollector):
    """
    Коллектор автомобильных новостей и аналитики авторынка РФ.
    Регламент запуска: Раз в неделю.
    Формат: latest_autonews.json (page_content + metadata).
    """

    def __init__(self):
        super().__init__("auto_news")
        self.output_file = NEWS_DIR / "latest_autonews.json"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
            "Referer": "https://yandex.ru/"
        })

    def fetch_full_text(self, url: str) -> str:
        """Извлечение полного текста статьи с новостного сайта"""
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding
                soup = BeautifulSoup(resp.text, "html.parser")

                for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
                    element.decompose()

                article_body = (
                    soup.find("article") or
                    soup.find("div", itemprop="articleBody") or
                    soup.find("div", class_=re.compile("article__text|news-text|text-block|content|body", re.I))
                )

                paragraphs = article_body.find_all("p") if article_body else soup.find_all("p")
                full_text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
                full_text = clean_mojibake(full_text)

                if len(full_text) > 250:
                    return full_text
        except Exception as e:
            self.logger.debug(f"Не удалось спарсить полный текст {url}: {e}")
        return ""

    def collect_from_rss_fallback(self, existing_urls: Set[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Фоллбэк на официальные RSS-ленты автомобильных СМИ РФ, если API исчерпало лимит"""
        self.logger.info("Сбор новостей через резервные RSS-ленты...")
        rss_docs = []

        for feed_url in FALLBACK_RSS_FEEDS:
            try:
                resp = self.session.get(feed_url, timeout=12)
                if resp.status_code != 200:
                    continue

                root = ET.fromstring(resp.content)
                for item in root.findall(".//item"):
                    title = item.findtext("title") or ""
                    link = item.findtext("link") or ""
                    pub_date = item.findtext("pubDate") or datetime.now().isoformat()
                    description = item.findtext("description") or ""

                    title = clean_mojibake(title.strip())
                    description = clean_mojibake(description.strip())

                    if not link or not title or link in existing_urls:
                        continue

                    title_lower = title.lower()
                    if any(sw in title_lower for sw in STOP_WORDS):
                        continue

                    existing_urls.add(link)
                    full_text = self.fetch_full_text(link)
                    content_to_store = full_text if full_text else description

                    rss_docs.append({
                        "page_content": f"Заголовок: {title}\nСодержание: {content_to_store}",
                        "metadata": {
                            "title": title,
                            "url": link,
                            "date": pub_date,
                            "source": "rss_feed",
                            "matched_query": "auto_rss",
                            "is_full_text": bool(full_text),
                            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    })

                    if len(rss_docs) >= limit:
                        break
            except Exception as e:
                self.logger.warning(f"Ошибка чтения RSS {feed_url}: {e}")

        return rss_docs

    async def collect(self) -> Dict[str, Any]:
        self.logger.info("Запуск сбора автомобильных новостей через NewsData API...")

        unique_urls: Set[str] = set()
        seen_titles: Set[str] = set()
        rag_documents: List[Dict[str, Any]] = []

        # Загрузка существующих новостей для предотвращения дублей
        if self.output_file.exists():
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    old_docs = json.load(f)
                    for d in old_docs:
                        u = d.get("metadata", {}).get("url")
                        if u:
                            unique_urls.add(u)
            except Exception:
                pass

        api_success = False

        if NEWSDATA_API_KEY:
            for q in QUERIES:
                api_url = f"https://newsdata.io/api/1/latest?apikey={NEWSDATA_API_KEY}&qInTitle={q}&country=ru&language=ru"
                try:
                    resp = self.session.get(api_url, timeout=12)
                    data = resp.json()

                    if data.get("status") == "success":
                        api_success = True
                        results = data.get("results", [])
                        for article in results:
                            link = article.get("link")
                            title = clean_mojibake(article.get("title", "").strip())
                            snippet = clean_mojibake(article.get("description", "") or "")

                            if not link or not title:
                                continue

                            clean_title = re.sub(r"[^\w\s]", "", title).lower()
                            if link in unique_urls or clean_title in seen_titles:
                                continue

                            title_lower = title.lower()
                            if any(sw in title_lower for sw in STOP_WORDS):
                                continue

                            unique_urls.add(link)
                            seen_titles.add(clean_title)

                            self.logger.info(f"Обработка статьи: {title[:55]}...")
                            full_text = self.fetch_full_text(link)
                            content_to_store = full_text if full_text else snippet

                            doc = {
                                "page_content": f"Заголовок: {title}\nСодержание: {content_to_store}",
                                "metadata": {
                                    "title": title,
                                    "url": link,
                                    "date": article.get("pubDate"),
                                    "source": article.get("source_id", "newsdata.io"),
                                    "matched_query": q,
                                    "is_full_text": bool(full_text),
                                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                            }
                            rag_documents.append(doc)

                            if len(rag_documents) >= 50:
                                break
                    elif "rate limit" in str(data).lower():
                        self.logger.warning("Достигнут суточный лимит запросов к NewsData API.")
                        break
                except Exception as api_err:
                    self.logger.warning(f"Ошибка запроса API для {q}: {api_err}")

        # Если через API собрано мало статей (или закончились кредиты) — подключаем RSS фоллбэк
        if len(rag_documents) < 20:
            fallback_items = self.collect_from_rss_fallback(unique_urls, limit=50 - len(rag_documents))
            rag_documents.extend(fallback_items)

        # Сохранение итогового файла
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(rag_documents, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Итоговый файл новостей сохранен: {self.output_file} ({len(rag_documents)} статей)")

        return {
            "items_collected": len(rag_documents),
            "output_file": str(self.output_file)
        }
