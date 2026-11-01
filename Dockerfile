FROM harbor.tools.telstra.com/public-cache/library/python:3.12

WORKDIR /app

ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-install-project

COPY . .
RUN chmod +x start.sh

# Override ECOS_MONGODB_URI at deploy time to point at your MongoDB.
ENV ECOS_MONGODB_URI="mongodb://host.docker.internal:27017" \
    ECOS_MONGODB_DB="Food_Recipe" \
    STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8000 8501

CMD ["python", "app.py"]
