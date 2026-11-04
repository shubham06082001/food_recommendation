import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip().strip("'\"")


def _mongodb_uri() -> str:
    if uri := _env("ECOS_MONGODB_URI"):
        return uri
    host = _env("DB_URL", "localhost:27017")
    # host.docker.internal only resolves inside containers.
    if not Path("/.dockerenv").exists():
        host = host.replace("host.docker.internal", "localhost")
    user, password = _env("DB_USERNAME"), _env("DB_PASSWORD")
    if user and password:
        return f"mongodb://{quote_plus(user)}:{quote_plus(password)}@{host}"
    return f"mongodb://{host}"


class Settings:
    mongodb_uri = _mongodb_uri()
    mongodb_db = _env("ECOS_MONGODB_DB", "Food_Recipe")
    manager_id = _env("ECOS_MANAGER_ID", "MGR001").upper()
    manager_password = _env("ECOS_MANAGER_PASSWORD")
    seed_demo = _env("ECOS_SEED_DEMO", "false").lower() == "true"
    semantic = _env("ECOS_SEMANTIC", "true").lower() == "true"  # false: goal-based ranking only (small hosts)
    catalog_refresh_hours = float(_env("ECOS_CATALOG_REFRESH_HOURS", "24"))
    qdrant_url = _env("QDRANT_VECTOR_DB_URL")
    qdrant_api_key = _env("QDRANT_API_KEY")


settings = Settings()
