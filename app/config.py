import os
from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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

    model_config = {"env_file": PROJECT_ROOT / ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def ensure_dirs():
    dirs = [
        PROJECT_ROOT / "data" / "submissions",
        PROJECT_ROOT / "data" / "chroma",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
