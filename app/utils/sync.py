import logging
import hashlib
import json
import asyncio
import shutil
import socket
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SYNC_TIMEOUT = 30

_LOCAL_CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"
_LOCAL_VERSION_FILE = Path(__file__).resolve().parent.parent.parent / "data" / ".config_version"


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


def pull_configs_from_server(dry_run: bool = True) -> str:
    if not is_sync_enabled():
        return "未配置中央服务器（SYNC_SERVER_URL 为空），无法同步配置。"

    url = _build_url("/api/v1/sync/configs")
    logger.info(f"Pulling configs from {url}")

    try:
        resp = httpx.get(url, timeout=SYNC_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"拉取配置失败: {e}"

    remote_version = data.get("version", "unknown")
    remote_files = data.get("files", {})

    local_version = ""
    if _LOCAL_VERSION_FILE.exists():
        local_version = _LOCAL_VERSION_FILE.read_text().strip()

    if remote_version == local_version:
        return f" 本地配置已是最新版本 ({remote_version})，无需同步。"

    added = []
    changed = []
    deleted = []

    for rel_path, remote_content in sorted(remote_files.items()):
        local_path = _LOCAL_CONFIGS_DIR / rel_path
        if not local_path.exists():
            added.append(rel_path)
        else:
            local_content = local_path.read_text(encoding="utf-8")
            if local_content.rstrip() != remote_content.rstrip():
                changed.append(rel_path)

    for local_file in sorted(_LOCAL_CONFIGS_DIR.rglob("*.json")):
        rel = str(local_file.relative_to(_LOCAL_CONFIGS_DIR)).replace("\\", "/")
        if rel not in remote_files:
            deleted.append(rel)

    if not added and not changed and not deleted:
        _LOCAL_VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LOCAL_VERSION_FILE.write_text(remote_version)
        return f" 配置文件无差异，但版本号已更新至 {remote_version}。"

    lines = [f"## 配置同步预览", ""]
    lines.append(f"**中央版本**: `{remote_version}`")
    lines.append(f"**本地版本**: `{local_version or '(无)'}`")
    lines.append("")
    lines.append(f"| 操作 | 文件 |")
    lines.append(f"|------|------|")
    for f in sorted(added):
        lines.append(f"|  新增 | {f} |")
    for f in sorted(changed):
        lines.append(f"|  更新 | {f} |")
    for f in sorted(deleted):
        lines.append(f"|  删除 | {f} |")
    lines.append("")

    if dry_run:
        lines.append(">  以上为预览。点击「确认同步」执行覆盖。")
        return "\n".join(lines)

    backup_dir = _LOCAL_CONFIGS_DIR.parent / "data" / f"configs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if _LOCAL_CONFIGS_DIR.exists():
        shutil.copytree(_LOCAL_CONFIGS_DIR, backup_dir)

    for rel_path, content in remote_files.items():
        local_path = _LOCAL_CONFIGS_DIR / rel_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding="utf-8")

    lines.append(f" 已应用 {len(added) + len(changed)} 个变更，旧配置备份至 `{backup_dir}`")
    lines.append(f" 中央版本 `{remote_version}` 同步完成。")

    _LOCAL_VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCAL_VERSION_FILE.write_text(remote_version)

    return "\n".join(lines)
