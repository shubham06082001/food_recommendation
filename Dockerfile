# Slim image for free-tier hosts: only what the app imports (no notebooks, TensorFlow or LangChain stack).
# Override BASE_IMAGE to use a private registry mirror.
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/app/.cache/huggingface \
    STREAMLIT_SERVER_HEADLESS=true STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app
COPY requirements.txt .
# CPU-only torch keeps the image small; the embedding model is baked in so start-up needs no download.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt \
    && python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY app.py ./
COPY backend ./backend
COPY dashboard ./dashboard
COPY ml ./ml
COPY .streamlit ./.streamlit

RUN useradd -m -u 1000 ecos && chown -R ecos:ecos /app
USER ecos

# Hosts inject PORT (Hugging Face Spaces uses 7860). Only the Streamlit UI listens publicly; the API stays on 127.0.0.1.
ENV PORT=7860
EXPOSE 7860
CMD ["python", "app.py"]
