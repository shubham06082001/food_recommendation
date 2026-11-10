# ECOS - Enterprise Cafeteria Operating System

An integrated FastAPI, Streamlit, and MongoDB project connecting employee meal choices with cafeteria ordering, inventory, recommendations, forecasting, and managerial decision support.

## Project documentation

- [Application and demonstration guide](docs/APP_GUIDE.md): setup, all role workflows, module capabilities, operating controls, demo sequence, and limitations.
- [Modular API catalog](api.json): backend operations grouped by the architecture, request/response types, and synthetic examples.
- [MBA final project report](docs/FINAL_PROJECT_REPORT.md): management-centered final-integration analysis, evidence boundaries, operating model, investment assumptions, governance, and benefits evaluation.
- [Original architecture](Architecture.png) and [implemented module connections](docs/assets/module-connections.svg).
- [Existing API endpoint notes](API_ENDPOINTS.md).

## Quick start

### Share And Rebuild In VS Code

Prerequisites on the recipient's machine: Docker Desktop (running), Python 3 available as `python3` on the host, VS Code, and the Dev Containers extension. Initial dependency/model downloads require internet access. On Windows, open the project from WSL with Docker Desktop integration enabled.

Include `.devcontainer/`, `env.template`, and both files in `qdrant-snapshot/` in the ZIP. Exclude `.env`, `.venv/`, `.git/`, `.devcontainer/host-ca.pem`, and private reports or credentials. Open the extracted folder in VS Code and run **Dev Containers: Rebuild and Reopen in Container**.

The host initialization hook reuses services on MongoDB port **20000** and Qdrant port **6333**. If unavailable, it starts existing containers bound to those ports; only when none exist does it create `ecos-mongodb` / `ecos-qdrant`, using named storage volumes and `unless-stopped` restart policies. No Compose stack is required. A conflicting service or invalid database credentials causes startup to fail rather than replacing data.

Only absent `food_nutrients` and `ecos_ingredients` collections are restored from the bundled snapshots. Existing collections are never overwritten; empty/unhealthy collections fail verification and require manual attention. Snapshot uploads use the host API, so the snapshot directory need not be mounted into Qdrant. Both collections must be readable and nonempty.

The hook creates or updates `.env` with `mongodb://host.docker.internal:20000` and `http://host.docker.internal:6333`. Configure database authentication and `QDRANT_API_KEY` in `.env` before reopening when reusing protected services. A fresh setup generates a manager password in `.env` without logging it; login ID defaults to `MGR001`.

The development container installs runtime dependencies separately from any host `.venv`, caches the recommendation embedding model in `ecos-model-cache`, and automatically starts the API and UI. Open **http://localhost:8501** (UI) or **http://localhost:8000/docs** (API). Startup logs are in `/tmp/ecos-app.log` inside the devcontainer.

Public CA certificates are regenerated from the recipient's host trust store for verified downloads on corporate networks; private keys and personal identity certificates are not exported. Installation bypasses inherited proxy settings by default, matching this project's local setup; set `ECOS_INSTALL_USE_PROXY=true` in the container environment if your network requires a working proxy.

Closing or rebuilding the devcontainer does not stop or remove the separate database containers or their volumes. Avoid `docker volume prune` or manually removing those volumes. To perform a read-only host check:

```bash
python3 .devcontainer/services.py --check
python3 -B .devcontainer/test_services.py
```

### Manual Python Setup

Use Python 3.12+, a configured MongoDB instance, and an authorized catalog/recipe provisioning path:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp env.template .env
# Configure private database/service settings and a strong manager password locally.
.venv/bin/python app.py
```

Default UI: `http://localhost:8501`. Local backend: `http://localhost:8000/api/v1`; Swagger: `http://localhost:8000/docs`.

Read the [setup prerequisites and configuration caveats](docs/APP_GUIDE.md#8-running-the-project-safely) before running against real data. A fresh Qdrant service does not include the `food_nutrients` dataset. The application uses mock payments, two enforced roles, and simplified procurement; project documentation distinguishes implemented functions from target-architecture aspirations and proposed business benefits.
