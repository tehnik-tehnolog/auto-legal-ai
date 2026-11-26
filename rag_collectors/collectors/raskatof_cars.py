import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None
import urllib.request

from collectors.base import BaseCollector
from config.settings import CARS_DIR, HTTP_TIMEOUT, RASKATOF_URL, USER_AGENT


class CarsCollector(BaseCollector):
    """
    Collector for available vehicles catalog from raskatof.ru.
    Schedule: Weekly.
    Output: structured vehicle cards (cars_raskatof.json) and RAG docs (cars_raskatof_rag.json).
    """

    def __init__(self):
        super().__init__("raskatof_cars")
        self.output_json = CARS_DIR / "cars_raskatof.json"
        self.output_rag = CARS_DIR / "cars_raskatof_rag.json"

    async def collect(self) -> Dict[str, Any]:
        self.logger.info(f"Запрос каталога авто с {RASKATOF_URL}...")

        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        response = requests.get(RASKATOF_URL, headers=headers, timeout=HTTP_TIMEOUT)
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка ответа сервера raskatof.ru: HTTP {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        choose_items = soup.find_all("div", class_="choose-item")
        self.logger.info(f"Найдено блоков с автомобилями: {len(choose_items)}")

        cars_data: List[Dict[str, Any]] = []
        rag_documents: List[Dict[str, Any]] = []
        current_category = "Эконом и комфорт класс"

        for item in choose_items:
            # Track vehicle class transition (Business / Economy)
            prev_heading = item.find_previous("h3", class_="section-subtitle")
            if prev_heading and "Бизнес" in prev_heading.get_text():
                current_category = "Бизнес класс"

            # Model name
            model_elem = item.find("h4", class_="choose-model")
            model_name = model_elem.get_text(strip=True) if model_elem else "Не указано"

            # Vehicle specs
            specs = {}
            specs_container = item.find("div", class_="choose-basic-specs")
            if specs_container:
                for p in specs_container.find_all("p"):
                    text = p.get_text(strip=True)
                    if ":" in text:
                        key, val = text.split(":", 1)
                        specs[key.strip()] = val.strip()

            # Trim features
            features = []
            features_container = item.find("div", class_="extra-features")
            if features_container:
                li_items = features_container.find_all("li")
                if li_items:
                    features = [li.get_text(strip=True) for li in li_items]
                else:
                    p_text = features_container.find("p")
                    if p_text:
                        features = [p_text.get_text(strip=True)]

            # Rental / buyout terms
            leasing_info = {}
            leasing_container = item.find("div", class_="leasing-info")
            if leasing_container:
                for p in leasing_container.find_all("p"):
                    text = p.get_text(strip=True)
                    if "Аренда" in text or "сутки" in text:
                        leasing_info["daily_rate"] = text
                    elif "взнос" in text:
                        leasing_info["initial_payment"] = text

            car_obj = {
                "category": current_category,
                "model": model_name,
                "specifications": specs,
                "features": features,
                "leasing_terms": leasing_info,
                "source_url": RASKATOF_URL,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            cars_data.append(car_obj)

            # Generate structured text document for RAG vector store
            specs_text = ", ".join([f"{k}: {v}" for k, v in specs.items()]) if specs else "не указаны"
            features_text = "; ".join(features) if features else "стандартная комплектация"
            daily = leasing_info.get("daily_rate", "уточняйте")
            initial = leasing_info.get("initial_payment", "уточняйте")

            page_content = (
                f"Автомобиль: {model_name}\n"
                f"Класс: {current_category}\n"
                f"Характеристики: {specs_text}\n"
                f"Комплектация и опции: {features_text}\n"
                f"Условия раската (выкупа/аренды): {daily}, первый взнос: {initial}.\n"
                f"Источник: Официальный сайт raskatof.ru"
            )

            rag_documents.append({
                "page_content": page_content,
                "metadata": {
                    "model": model_name,
                    "category": current_category,
                    "daily_rate": daily,
                    "initial_payment": initial,
                    "source": "raskatof.ru",
                    "doc_type": "vehicle_catalog",
                    "updated_at": car_obj["updated_at"]
                }
            })

        # Persist both catalog JSON and RAG JSON formats
        with open(self.output_json, "w", encoding="utf-8") as f:
            json.dump(cars_data, f, ensure_ascii=False, indent=2)

        with open(self.output_rag, "w", encoding="utf-8") as f:
            json.dump(rag_documents, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Каталог успешно сохранен: {self.output_json} ({len(cars_data)} авто)")
        self.logger.info(f"RAG-документы сохранены: {self.output_rag}")

        return {
            "items_collected": len(cars_data),
            "output_catalog": str(self.output_json),
            "output_rag": str(self.output_rag)
        }
