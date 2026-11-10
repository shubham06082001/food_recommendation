#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export NO_PROXY="localhost,127.0.0.1,host.docker.internal,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"
PYTHON=/opt/ecos-venv/bin/python
"$PYTHON" - <<'PY'
from pymongo import MongoClient
from backend.app.core.config import settings
from backend.app.core.vectors import qdrant

with MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=15000) as client:
    client.admin.command("ping")
for name in ("food_nutrients", "ecos_ingredients"):
    collection = qdrant().get_collection(name)
    if not collection.points_count:
        raise SystemExit(f"Qdrant collection {name} is empty")
print("MongoDB authenticated ping and both Qdrant collections verified.")
PY
if "$PYTHON" - <<'PY'
import urllib.request
from app import backend_up
try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("http://127.0.0.1:8501/_stcore/health", timeout=2) as response:
        raise SystemExit(0 if backend_up() and response.status == 200 else 1)
except OSError:
    raise SystemExit(1)
PY
then
    echo "ECOS API and UI already running; preserving the existing app process."
else
    nohup "$PYTHON" app.py > /tmp/ecos-app.log 2>&1 < /dev/null &
fi
"$PYTHON" - <<'PY'
import time
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for attempt in range(180):
    try:
        for url in ("http://127.0.0.1:8000/api/v1/health", "http://127.0.0.1:8501/_stcore/health"):
            with opener.open(url, timeout=2) as response:
                if response.status != 200:
                    raise OSError("App is not healthy yet")
        print("ECOS ready: UI http://localhost:8501 | API http://localhost:8000/docs")
        break
    except OSError:
        if attempt == 179:
            raise SystemExit("App startup failed; inspect /tmp/ecos-app.log")
        time.sleep(1)
PY