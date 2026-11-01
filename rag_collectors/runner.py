#!/usr/bin/env python3
"""
Мастер-скрипт запуска коллекторов данных для RAG-ассистента раската авто в РФ.
Поддерживает запуск отдельных коллекторов по крону, пакетный запуск и проверку статуса базы.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from config.settings import CARS_DIR, COURT_DIR, DATA_DIR, LEGAL_DIR, NEWS_DIR


def print_status_dashboard():
    """Вывод актуального состояния собранной RAG-базы на сервере"""
    print("\n" + "=" * 70)
    print("📊 ТЕКУЩЕЕ СОСТОЯНИЕ БАЗЫ ДАННЫХ RAG (РАСКАТ АВТО)")
    print("=" * 70)

    # 1. Законы (ГК РФ / НК РФ)
    law_files = list(LEGAL_DIR.glob("*.md"))
    law_size_kb = sum(f.stat().st_size for f in law_files) / 1024 if law_files else 0
    print(f"1. 📜 Нормативная база (ГК/НК РФ):")
    print(f"   - Документов (.md): {len(law_files)}")
    print(f"   - Общий объем:      {law_size_kb:.1f} КБ")
    print(f"   - Директория:       {LEGAL_DIR}")
    print(f"   - Регламент:        Раз в 3 месяца")

    # 2. Судебная практика ВС РФ
    vsrf_file = COURT_DIR / "vsrf_court_docs_rag.json"
    vsrf_count = 0
    if vsrf_file.exists():
        try:
            with open(vsrf_file, "r", encoding="utf-8") as f:
                vsrf_count = len(json.load(f))
        except Exception:
            pass
    print(f"\n2. ⚖️ Судебная практика ВС РФ:")
    print(f"   - Обработано актов: {vsrf_count} шт.")
    print(f"   - Файл:             {vsrf_file}")
    print(f"   - Регламент:        Раз в месяц")

    # 3. Ассортимент машин raskatof.ru
    cars_file = CARS_DIR / "cars_raskatof.json"
    cars_count = 0
    if cars_file.exists():
        try:
            with open(cars_file, "r", encoding="utf-8") as f:
                cars_count = len(json.load(f))
        except Exception:
            pass
    print(f"\n3. 🚗 Ассортимент машин (raskatof.ru):")
    print(f"   - Карточек в базе:  {cars_count} авто")
    print(f"   - Файл:             {cars_file}")
    print(f"   - Регламент:        Раз в неделю")

    # 4. Автомобильные новости
    news_file = NEWS_DIR / "latest_autonews.json"
    news_count = 0
    if news_file.exists():
        try:
            with open(news_file, "r", encoding="utf-8") as f:
                news_count = len(json.load(f))
        except Exception:
            pass
    print(f"\n4. 📰 Автомобильные новости:")
    print(f"   - Статей в базе:    {news_count} шт.")
    print(f"   - Файл:             {news_file}")
    print(f"   - Регламент:        Раз в неделю")
    print("=" * 70 + "\n")


async def run_collector(collector_name: str) -> bool:
    """Запуск выбранного коллектора"""
    from collectors.auto_news import AutoNewsCollector
    from collectors.gk_nk_laws import LawsCollector
    from collectors.raskatof_cars import CarsCollector
    from collectors.vsrf_court import VSRFCourtCollector

    collectors_map = {
        "laws": LawsCollector,
        "vsrf": VSRFCourtCollector,
        "cars": CarsCollector,
        "news": AutoNewsCollector
    }

    if collector_name not in collectors_map and collector_name != "all":
        print(f"❌ Неизвестный коллектор: {collector_name}")
        print(f"Допустимые варианты: {', '.join(collectors_map.keys())}, all")
        return False

    targets = list(collectors_map.keys()) if collector_name == "all" else [collector_name]
    all_success = True

    for target in targets:
        collector_cls = collectors_map[target]
        collector_instance = collector_cls()
        stats = await collector_instance.run()
        if not stats.get("success", False):
            all_success = False

    return all_success


def main():
    parser = argparse.ArgumentParser(
        description="RAG Data Collectors Orchestrator для компании по раскату авто"
    )
    parser.add_argument(
        "--collector",
        choices=["laws", "vsrf", "cars", "news", "all"],
        help="Какой коллектор запустить (laws=ГК/НК РФ, vsrf=ВС РФ, cars=raskatof.ru, news=автоновости, all=все)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Показать текущую статистику собранных файлов в базе RAG"
    )

    args = parser.parse_args()

    if args.status:
        print_status_dashboard()
        return

    if not args.collector:
        parser.print_help()
        print("\nПримеры использования на сервере:")
        print("  python runner.py --collector cars     # Запуск сбора машин (еженедельно)")
        print("  python runner.py --collector news     # Запуск сбора новостей (еженедельно)")
        print("  python runner.py --collector vsrf     # Запуск сбора ВС РФ (ежемесячно)")
        print("  python runner.py --collector laws     # Запуск сбора законов (раз в 3 мес)")
        print("  python runner.py --status             # Показать объем собранных данных")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    success = asyncio.run(run_collector(args.collector))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
