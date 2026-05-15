import logging
import json
import asyncio
import socket

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SYNC_TIMEOUT = 30


def _get_instance_name() -> str:
    name = settings.instance_name.strip()
    if name:
        return name
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def is_sync_enabled() -> bool:
    return bool(settings.sync_server_url.strip())


def _build_url(path: str) -> str:
    base = settings.sync_server_url.rstrip("/")
    return f"{base}{path}"


async def _post_json(path: str, payload: dict) -> bool:
    if not is_sync_enabled():
        return False
    url = _build_url(path)
    try:
        async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info(f"Synced to central server: {path}")
                return True
            else:
                logger.warning(f"Sync failed {path}: HTTP {resp.status_code} {resp.text[:200]}")
                return False
    except Exception as e:
        logger.warning(f"Sync failed {path}: {e}")
        return False


async def report_review(review_data: dict):
    payload = {
        "instance_name": _get_instance_name(),
        **review_data,
    }
    asyncio.ensure_future(_post_json("/api/v1/sync/review", payload))


async def report_calibration(calibration_data: dict):
    payload = {
        "instance_name": _get_instance_name(),
        **calibration_data,
    }
    asyncio.ensure_future(_post_json("/api/v1/sync/calibration", payload))
