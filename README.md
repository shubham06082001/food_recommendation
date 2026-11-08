# ECOS - Enterprise Cafeteria Operating System

An integrated FastAPI, Streamlit, and MongoDB project connecting employee meal choices with cafeteria ordering, inventory, recommendations, forecasting, and managerial decision support.

## Project documentation

- [Application and demonstration guide](docs/APP_GUIDE.md): setup, all role workflows, module capabilities, operating controls, demo sequence, and limitations.
- [Modular API catalog](api.json): backend operations grouped by the architecture, request/response types, and synthetic examples.
- [MBA final project report](docs/FINAL_PROJECT_REPORT.md): management-centered final-integration analysis, evidence boundaries, operating model, investment assumptions, governance, and benefits evaluation.
- [Original architecture](Architecture.png) and [implemented module connections](docs/assets/module-connections.svg).
- [Existing API endpoint notes](API_ENDPOINTS.md).

## Quick start

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
