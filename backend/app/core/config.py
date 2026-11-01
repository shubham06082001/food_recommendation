import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")


def _mongodb_uri() -> str:
    uri = os.getenv("ECOS_MONGODB_URI")
    if uri:
        return uri
    host = os.getenv("DB_URL", "localhost:27017").strip("'\"")
    # host.docker.internal only resolves inside containers.
    if not Path("/.dockerenv").exists():
        host = host.replace("host.docker.internal", "localhost")
    user, password = os.getenv("DB_USERNAME", ""), os.getenv("DB_PASSWORD", "")
    if user and password:
        return f"mongodb://{quote_plus(user)}:{quote_plus(password)}@{host}"
    return f"mongodb://{host}"


class Settings:
    mongodb_uri = _mongodb_uri()
    mongodb_db = os.getenv("ECOS_MONGODB_DB", "Food_Recipe")
    seed_on_startup = os.getenv("ECOS_SEED_ON_STARTUP", "true").lower() == "true"


settings = Settings()
