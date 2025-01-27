import asyncio
import json
import logging
import sys
from asyncio.queues import Queue
from typing import Optional
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

import colorlog
import yaml
import os

from sqlalchemy.exc import OperationalError

from chia.util.streamable import dataclass_from_dict
from chia.consensus.block_record import BlockRecord


def from_json_dict(json_dict: Dict) -> Any:
    if 'farmer_public_key' in json_dict:
        json_dict.pop('farmer_public_key')
    return dataclass_from_dict(BlockRecord, json_dict)

setattr(BlockRecord, 'from_json_dict', from_json_dict)

from monitor.collectors import RpcCollector, WsCollector
from monitor.collectors.price_collector import PriceCollector
from monitor.database import GoldEvent, session
from monitor.exporter import GoldExporter
from monitor.logger import GoldLogger
from monitor.notifier import Notifier


def config_path_for_filename(root_path: Path, filename: Union[str, Path]) -> Path:
    path_filename = Path(filename)
    if path_filename.is_absolute():
        return path_filename
    return root_path / "config" / filename


def load_config(
        root_path: Path,
        filename: Union[str, Path],
        sub_config: Optional[str] = None,
        exit_on_error=True,
) -> Dict:
    path = config_path_for_filename(root_path, filename)
    if not path.is_file():
        if not exit_on_error:
            raise ValueError("Config not found")
        print(f"can't find {path}")
        print("** please run `gold init` to migrate or create new config files **")
        # TODO: fix this hack
        sys.exit(-1)
    r = yaml.safe_load(open(path, "r"))
    if sub_config is not None:
        r = r.get(sub_config)
    return r


DEFAULT_ROOT_PATH = Path(os.path.expanduser(os.getenv("GOLD_ROOT", "~/.gold/mainnet"))).resolve()
gold_config = load_config(DEFAULT_ROOT_PATH, "config.yaml")


def initilize_logging():
    handler = colorlog.StreamHandler()
    log_date_format = "%Y-%m-%dT%H:%M:%S"
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(asctime)s.%(msecs)03d %(log_color)s%(levelname)-6s%(reset)s %(message)s",
            datefmt=log_date_format,
            reset=True,
        ))
    logger = colorlog.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def persist_event(event: GoldEvent):
    with session.begin() as db_session:
        db_session.add(event)
        db_session.commit()


async def aggregator(exporter: GoldExporter, notifier: Optional[Notifier], rpc_refresh_interval: int,
                     price_refresh_interval: int) -> None:
    rpc_collector = None
    ws_collector = None
    event_queue = Queue()
    logger = GoldLogger()

    try:
        logging.info("🔌 Creating RPC Collector...")
        rpc_collector = await RpcCollector.create(DEFAULT_ROOT_PATH, gold_config, event_queue, rpc_refresh_interval)
    except Exception as e:
        logging.warning(f"Failed to create RPC collector. Continuing without it. {type(e).__name__}: {e}")

    try:
        logging.info("🔌 Creating WebSocket Collector...")
        ws_collector = await WsCollector.create(DEFAULT_ROOT_PATH, gold_config, event_queue)
    except Exception as e:
        logging.warning(f"Failed to create WebSocket collector. Continuing without it. {type(e).__name__}: {e}")

    try:
        logging.info("🔌 Creating Price Collector...")
        price_collector = await PriceCollector.create(DEFAULT_ROOT_PATH, gold_config, event_queue,
                                                      price_refresh_interval)
    except Exception as e:
        logging.warning(f"Failed to create Price collector. Continuing without it. {type(e).__name__}: {e}")

    if rpc_collector and ws_collector:
        logging.info("🚀 Starting monitoring loop!")
        rpc_task = asyncio.create_task(rpc_collector.task())
        ws_task = asyncio.create_task(ws_collector.task())
        if notifier is not None:
            notifier.start()
        if price_collector is not None:
            asyncio.create_task(price_collector.task())
        while True:
            try:
                event = await event_queue.get()
                exporter.process_event(event)
                logger.process_event(event)
                persist_event(event)

            except OperationalError:
                logging.exception(
                    f"Failed to persist event to DB. Please initialize DB using: 'pipenv run alembic upgrade head'")
                break

            except asyncio.CancelledError:
                break

    else:
        logging.error("Failed to create any collector.")

    logging.info("🛑 Shutting down!")
    if rpc_collector:
        rpc_task.cancel()
        await rpc_collector.close()
    if ws_collector:
        ws_task.cancel()
        await ws_collector.close()
    if notifier:
        notifier.stop()


def read_config():
    with open("config.json") as f:
        config = json.load(f)
    return config


if __name__ == "__main__":
    initilize_logging()
    try:
        config = read_config()
    except:
        logging.error(
            "Failed to read config.json. Please copy the config-example.json to config.json and configure it to your preferences."
        )
        sys.exit(1)

    try:
        exporter_port = config["exporter_port"]
        rpc_refresh_interval = config["rpc_collector"]["refresh_interval_seconds"]
        price_refresh_interval = enable_notifications = config["price_collector"]["refresh_interval_seconds"]
        enable_notifications = config["notifications"]["enable"]
        notifications_refresh_interval = config["notifications"]["refresh_interval_seconds"]
        status_url = config["notifications"]["status_service_url"]
        alert_url = config["notifications"]["alert_service_url"]
        status_interval_minutes = config["notifications"]["status_interval_minutes"]
        lost_plots_alert_threshold = config["notifications"]["lost_plots_alert_threshold"]
        disable_proof_found_alert = config["notifications"]["disable_proof_found_alert"]
    except KeyError as ex:
        logging.error(
            f"Failed to validate config. Missing required key {ex}. Please compare the fields of your config.json with the config-example.json and fix all inconsistencies."
        )
        sys.exit(1)

    exporter = GoldExporter(exporter_port)
    if enable_notifications:
        notifier = Notifier(status_url, alert_url, status_interval_minutes, lost_plots_alert_threshold,
                            disable_proof_found_alert, notifications_refresh_interval)
    else:
        notifier = None

    try:
        asyncio.run(aggregator(exporter, notifier, rpc_refresh_interval, price_refresh_interval))
    except KeyboardInterrupt:
        logging.info("👋 Bye!")
