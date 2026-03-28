"""
simulator.py — Симулятор узлов цепи поставок.

Читает sample_data.json, генерирует данные и отправляет на API.

Использование:
  python -m simulator.simulator              # разовый запуск
  python -m simulator.simulator --loop       # бесконечный loop
  python -m simulator.simulator --loop --interval 10  # loop каждые 10 сек
  python -m simulator.simulator --file my_data.json   # свой файл данных
"""

import httpx
import json
import time
import random
import argparse
import logging
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Настройка логирования
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("simulator")

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

API_URL = "http://127.0.0.1:8000"
DEFAULT_DATA_FILE = Path(__file__).parent.parent / "sample_data.json"
DEFAULT_INTERVAL = 5  # секунд между итерациями в loop режиме


# ---------------------------------------------------------------------------
# Генерация данных с реалистичным шумом
# ---------------------------------------------------------------------------

def add_noise(event: dict) -> dict:
    """
    Добавляем случайный шум к данным — имитация реальных колебаний.

    stock:          ±10% от базового значения
    daily_usage:    ±5% от базового значения
    delivery_delay: случайное смещение -1..+3 дня (задержки чаще чем опережения)
    """
    noisy = event.copy()

    noisy["stock"] = round(
        event["stock"] * random.uniform(0.90, 1.10), 1
    )
    noisy["daily_usage"] = round(
        event["daily_usage"] * random.uniform(0.95, 1.05), 1
    )
    noisy["delivery_delay"] = max(
        0, round(event["delivery_delay"] + random.uniform(-1, 3), 1)
    )

    return noisy


def load_data(file_path: Path) -> list[dict]:
    """Загружаем seed-данные из JSON файла."""
    if not file_path.exists():
        raise FileNotFoundError(f"Файл данных не найден: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Файл данных должен содержать непустой массив объектов")

    log.info(f"Загружено {len(data)} записей из {file_path.name}")
    return data


# ---------------------------------------------------------------------------
# Отправка данных на API
# ---------------------------------------------------------------------------

def send_event(client: httpx.Client, event: dict) -> bool:
    """
    Отправляем одно событие на POST /data.
    Возвращает True если успешно, False если ошибка.
    """
    try:
        response = client.post(f"{API_URL}/data", json=event, timeout=5.0)

        if response.status_code == 201:
            result = response.json()
            log.info(
                f"✅ Отправлено | id={result['id']} | "
                f"склад={result['warehouse_id']} | "
                f"товар={result['product']} | "
                f"остаток={result['stock']} | "
                f"задержка={result['delivery_delay']} дн."
            )
            return True

        elif response.status_code == 422:
            errors = response.json().get("detail", [])
            log.warning(f"⚠️  Ошибка валидации для {event}: {errors}")
            return False

        else:
            log.error(f"❌ Неожиданный статус {response.status_code}: {response.text}")
            return False

    except httpx.ConnectError:
        log.error(f"❌ Не удалось подключиться к API на {API_URL}. Сервер запущен?")
        return False
    except httpx.TimeoutException:
        log.error("❌ Таймаут запроса к API")
        return False


def check_api_health(client: httpx.Client) -> bool:
    """Проверяем что API доступен перед началом работы."""
    try:
        response = client.get(f"{API_URL}/health", timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            log.info(f"✅ API доступен | версия={data['version']} | БД={data['db_connected']}")
            return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

def run_once(data: list[dict], use_noise: bool = True) -> dict:
    """
    Разовый запуск — отправляем все события из файла один раз.
    Возвращает статистику: сколько успешно, сколько с ошибкой.
    """
    stats = {"sent": 0, "failed": 0, "total": len(data)}

    with httpx.Client() as client:

        # Проверяем API
        if not check_api_health(client):
            log.error("❌ API недоступен. Запусти сервер: uvicorn api.main:app --reload --port 8000")
            return stats

        log.info(f"📦 Начинаем отправку {len(data)} событий...")

        for event in data:
            payload = add_noise(event) if use_noise else event
            success = send_event(client, payload)

            if success:
                stats["sent"] += 1
            else:
                stats["failed"] += 1

            # Небольшая пауза между запросами — не перегружаем API
            time.sleep(0.2)

    return stats


def run_loop(data: list[dict], interval: int, use_noise: bool = True):
    """
    Loop режим — повторяем отправку каждые N секунд.
    Останавливается по Ctrl+C.
    """
    iteration = 0

    log.info(f"🔄 Loop режим запущен. Интервал: {interval} сек. Остановка: Ctrl+C")

    while True:
        iteration += 1
        log.info(f"--- Итерация #{iteration} | {datetime.now().strftime('%H:%M:%S')} ---")

        stats = run_once(data, use_noise=use_noise)

        log.info(
            f"📊 Итерация #{iteration} завершена | "
            f"Отправлено: {stats['sent']}/{stats['total']} | "
            f"Ошибок: {stats['failed']}"
        )

        log.info(f"⏳ Следующая итерация через {interval} сек...")
        time.sleep(interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Симулятор узлов цепи поставок"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Запустить в бесконечном loop режиме"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Интервал между итерациями в секундах (default: {DEFAULT_INTERVAL})"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=str(DEFAULT_DATA_FILE),
        help="Путь к JSON файлу с данными"
    )
    parser.add_argument(
        "--no-noise",
        action="store_true",
        help="Отключить случайный шум (отправлять точные данные из файла)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    use_noise = not args.no_noise

    log.info("=" * 50)
    log.info("🚀 Supply Chain Node Simulator")
    log.info(f"   Файл данных: {args.file}")
    log.info(f"   Режим: {'loop' if args.loop else 'разовый'}")
    log.info(f"   Шум: {'включён' if use_noise else 'выключен'}")
    log.info("=" * 50)

    # Загружаем данные
    data = load_data(Path(args.file))

    # Запускаем нужный режим
    if args.loop:
        try:
            run_loop(data, interval=args.interval, use_noise=use_noise)
        except KeyboardInterrupt:
            log.info("\n⛔ Симулятор остановлен пользователем")
    else:
        stats = run_once(data, use_noise=use_noise)
        log.info("=" * 50)
        log.info(f"✅ Готово | Отправлено: {stats['sent']} | Ошибок: {stats['failed']}")


if __name__ == "__main__":
    main()
