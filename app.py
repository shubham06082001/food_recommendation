"""ECOS entry point: `python app.py` starts the FastAPI backend, waits for it, then opens the Streamlit dashboard.

`streamlit run app.py` still works and renders only the dashboard.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_PORT = os.getenv("API_PORT", "8000")
UI_PORT = os.getenv("UI_PORT", "8501")
HEALTH_URL = f"http://127.0.0.1:{API_PORT}/api/v1/health"
# Bypass corporate proxy settings for localhost health checks.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def backend_up() -> bool:
    try:
        with _opener.open(HEALTH_URL, timeout=2) as response:
            return response.status == 200
    except OSError:
        return False


def start_backend(env: dict) -> subprocess.Popen | None:
    if backend_up():
        print(f"ECOS backend already running on :{API_PORT}")
        return None
    print(f"Starting ECOS backend on :{API_PORT} ...")
    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app",
                                "--host", "0.0.0.0", "--port", API_PORT], cwd=ROOT, env=env)
    for _ in range(60):
        if backend_up():
            print("ECOS backend ready (MongoDB connected).")
            return backend
        if backend.poll() is not None:
            sys.exit("Backend exited. Is MongoDB reachable? Check ECOS_MONGODB_URI / DB_URL in .env.")
        time.sleep(1)
    backend.terminate()
    sys.exit("Backend did not become healthy within 60 seconds.")


def launch() -> None:
    env = {**os.environ, "ECOS_API_URL": f"http://127.0.0.1:{API_PORT}/api/v1"}
    backend = start_backend(env)
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(ROOT / "dashboard" / "app.py"),
                        "--server.address=0.0.0.0", f"--server.port={UI_PORT}"], cwd=ROOT, env=env, check=False)
    except KeyboardInterrupt:
        pass
    finally:
        if backend:
            backend.terminate()
            backend.wait(timeout=10)


if __name__ == "__main__":
    from streamlit import runtime

    if runtime.exists():
        from dashboard.app import main

        main()
    else:
        launch()
