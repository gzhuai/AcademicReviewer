import json
import os
from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_registry_cache = None
_alias_map = None


def _load_registry() -> dict:
    global _registry_cache
    if _registry_cache is None:
        path = PROJECT_ROOT / "configs" / "competition_registry.json"
        _registry_cache = json.loads(path.read_text(encoding="utf-8"))
    return _registry_cache


def _build_alias_map() -> dict[str, str]:
    global _alias_map
    if _alias_map is None:
        registry = _load_registry()
        _alias_map = {}
        for canonical, cfg in registry.get("competitions", {}).items():
            _alias_map[canonical.lower().strip()] = canonical
            for alias in cfg.get("aliases", []):
                _alias_map[alias.lower().strip()] = canonical
    return _alias_map


def clear_config_cache():
    """重置竞赛注册表缓存（用于测试或热加载场景）。"""
    global _registry_cache, _alias_map
    _registry_cache = None
    _alias_map = None


def normalize_competition_name(name: str) -> str:
    """将任意赛事名称归一化为 canonical name。支持英文全称/缩写/中英混写。"""
    if not name or not name.strip():
        return name
    key = name.strip().lower()
    alias_map = _build_alias_map()
    return alias_map.get(key, name.strip())


def get_competition_list() -> list[dict]:
    """返回竞赛下拉列表 [{name, type, type_cn, structure_schema, evidence_config, style_template}, ...]"""
    registry = _load_registry()
    types = registry.get("competition_types", {})
    result = []
    for name, cfg in registry.get("competitions", {}).items():
        result.append({
            "name": name,
            "type": cfg["type"],
            "type_cn": types.get(cfg["type"], cfg["type"]),
            "structure_schema": cfg.get("structure_schema", "research.json"),
            "evidence_config": cfg.get("evidence_config", "research.json"),
            "style_template": cfg.get("style_template", "tech_academic.json"),
        })
    return result


class Settings(BaseSettings):
    openai_api_key: str = ""
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    glm_api_key: str = ""

    llm_provider: str = "deepseek"

    database_url: str = f"sqlite:///{PROJECT_ROOT}/data/academic_reviewer.db"
    chroma_persist_dir: str = str(PROJECT_ROOT / "data" / "chroma")

    host: str = "127.0.0.1"
    port: int = 8000

    sync_server_url: str = ""
    instance_name: str = ""

    api_token: str = ""  # Leave empty to skip auth (backward compatible)

    model_config = {"env_file": PROJECT_ROOT / ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def ensure_dirs():
    dirs = [
        PROJECT_ROOT / "data" / "submissions",
        PROJECT_ROOT / "data" / "chroma",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
