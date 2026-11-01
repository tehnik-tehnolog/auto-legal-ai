import logging
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from config.settings import LOGS_DIR

def setup_logger(name: str) -> logging.Logger:
    """Настройка структурированного логирования для сервера"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Вывод в консоль (stdout для Docker и systemd journal)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Вывод в файл лога
        log_file = LOGS_DIR / f"{name}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class BaseCollector(ABC):
    """Базовый абстрактный класс для всех серверных коллекторов данных RAG"""

    def __init__(self, name: str):
        self.name = name
        self.logger = setup_logger(name)
        self.stats: Dict[str, Any] = {
            "name": name,
            "started_at": None,
            "completed_at": None,
            "duration_seconds": 0,
            "items_collected": 0,
            "errors_count": 0,
            "success": False
        }

    @abstractmethod
    async def collect(self) -> Dict[str, Any]:
        """Основной метод сбора данных, реализуемый каждым коллектором"""
        pass

    async def run(self) -> Dict[str, Any]:
        """Безопасный запуск с замером времени и сбором метрик"""
        start_time = time.time()
        self.stats["started_at"] = datetime.now().isoformat()
        self.logger.info(f"=== Запуск коллектора [{self.name}] ===")

        try:
            result = await self.collect()
            self.stats.update(result)
            self.stats["success"] = True
            self.logger.info(
                f"[SUCCESS] Коллектор [{self.name}] завершен. Собрано: {self.stats.get('items_collected', 0)} объектов."
            )
        except Exception as e:
            self.stats["errors_count"] += 1
            self.stats["success"] = False
            self.stats["error_message"] = str(e)
            self.logger.error(f"[ERROR] Ошибка в работе коллектора [{self.name}]: {e}", exc_info=True)
        finally:
            duration = round(time.time() - start_time, 2)
            self.stats["duration_seconds"] = duration
            self.stats["completed_at"] = datetime.now().isoformat()
            self.logger.info(f"=== Завершено за {duration} сек. ===")

        return self.stats
