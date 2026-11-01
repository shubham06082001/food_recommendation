# pylint: disable=C0301:line-too-long, W1203:logging-fstring-interpolation, C0114:missing-module-docstring

from __future__ import annotations

import logging
import os
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

import httpx
import numpy as np
from dotenv import load_dotenv
from openai import OpenAIError
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from langgraph.checkpoint.memory import MemorySaver

try:
    from langgraph.checkpoint.mongodb import MongoDBSaver
except ImportError:
    MongoDBSaver = None

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse


def get_local_qdrant_client(storage_path: str | Path) -> QdrantClient:
    """Return a persistent local Qdrant client for offline project search."""
    return QdrantClient(path=str(storage_path))


def get_neo4j_driver(
    uri: str | None = None,
    username: str | None = None,
    password: str | None = None,
):
    """Return a Neo4j driver configured from the local environment."""
    uri = uri or _getenv("NEO4J_URI", "")
    username = username or _getenv("NEO4J_USERNAME", "")
    password = password or _getenv("NEO4J_PASSWORD", "")
    if not uri or not username or not password:
        raise ValueError("NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD must be configured.")
    return GraphDatabase.driver(uri, auth=(username, password))


def check_neo4j_connection(
    database: str | None = None,
) -> tuple[bool, str]:
    """Check authentication and access to the configured Neo4j database."""
    database = database or _getenv("NEO4J_DATABASE", "neo4j")
    try:
        with get_neo4j_driver() as driver:
            driver.verify_connectivity(database=database)
            with driver.session(database=database) as session:
                session.run("RETURN 1 AS connected").single()
        return True, f"Neo4j reachable (database={database})"
    except (Neo4jError, OSError, RuntimeError, ValueError) as error:
        return False, f"Neo4j connection failed: {type(error).__name__}: {str(error)[:160]}"


def get_embedding_model(
    model_name: str = "all-MiniLM-L6-v2",
    local_files_only: bool = True,
) -> SentenceTransformer:
    """Load the cached sentence-transformer used for local semantic retrieval."""
    return SentenceTransformer(model_name, local_files_only=local_files_only)


def embed_texts(
    model: SentenceTransformer,
    texts: Iterable[str],
    batch_size: int = 64,
    dimensions: int | None = None,
) -> np.ndarray:
    """Create normalized float32 vectors, optionally truncated to a target dimension."""
    embeddings = model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    if dimensions is None:
        return embeddings
    if not 0 < dimensions <= embeddings.shape[1]:
        raise ValueError(
            f"dimensions must be between 1 and {embeddings.shape[1]}, got {dimensions}."
        )

    embeddings = embeddings[:, :dimensions]
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / np.clip(norms, a_min=np.float32(1e-12), a_max=None)


def try_embed_local_query(
    model: SentenceTransformer,
    query: str,
    dimensions: int | None = None,
) -> np.ndarray | None:
    """Embed a non-empty local query, returning None when no text is supplied."""
    query = str(query).strip()
    if not query:
        return None
    return embed_texts(model, [query], batch_size=1, dimensions=dimensions)[0]

# Load .env file from current directory or project root
env_file = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_file, override=True)


def _getenv(key: str, default: str = "") -> str:
    """Get environment variable and strip surrounding quotes if present."""
    value = os.getenv(key, default)
    # Strip surrounding quotes if present (handles "value" or 'value')
    if value and len(value) >= 2:
        if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
            value = value[1:-1]
    return value


# Constants for Models
MODEL_GPT_4O = "azure-gpt-4o"
MODEL_GPT_5 = "gpt-5-preprod"
CLAUDE_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"
GPT_5_MINI = "gpt-5-mini-preprod"
GPT_4O_MINI = "gpt-4o-mini"

# Embedding Models
TEXT_EMBEDDING = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 1536  # For text-embedding-3-small
DIMENSION_256=256
DIMENSION_512=512

# Environment Variables
OPENAI_API_KEY = _getenv("OPENAI_API_KEY", "")
BASE_URL = _getenv("BASE_URL", "")

# LangFuse Environment Variables
LANGFUSE_PUBLIC_KEY = _getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = _getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_BASE_URL = _getenv(
    "LANGFUSE_BASE_URL", "BASE_URL"  # Default to BASE_URL if not set
)

# Certificate Path for LLM and LangFuse connections
DEFAULT_CERT_PATH = _getenv(
    "LANGFUSE_CERT_PATH",
    str(Path(__file__).resolve().with_name("_.ibis.head-p2.puma.corp.telstra.com.pem")),
)

# Qdrant Vector DB Environment Variables
QDRANT_VECTOR_DB_URL = _getenv("QDRANT_VECTOR_DB_URL", "")
QDRANT_API_KEY = _getenv("QDRANT_API_KEY", "")
QDRANT_VECTOR_SIZE = 1536

QDRANT_SCHEMA_COLLECTION = "WDA_Schema_Collection"

# Neo4j graph database environment variables
NEO4J_URI = _getenv("NEO4J_URI", "")
NEO4J_USERNAME = _getenv("NEO4J_USERNAME", "")
NEO4J_PASSWORD = _getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = _getenv("NEO4J_DATABASE", "neo4j")

# Qdrant collections for Analytica - Stores: query memory fingerprints, audit logs, learning data
QDRANT_ANALYTICA_COLLECTION = "Analytica"
QDRANT_AUDIT_COLLECTION = "Analytica-Audit"
QDRANT_ANALYTICA_MEMORY_COLLECTION = "Analytica-Memory"
QDRANT_INSECURE_API_KEY_WARNING = "Api key is used with an insecure connection."



def _normalize_mongo_url(value: str) -> str:
    raw = value
    if "://" not in raw:
        raw = f"mongodb://{raw}"
    if raw.startswith("mongodb://host.docker.internal"):
        raw = raw.replace("mongodb://host.docker.internal", "mongodb://localhost", 1)
    return raw


@contextmanager
def _suppress_qdrant_insecure_warning():
    """Suppress known Qdrant warning for api_key over non-TLS URL in local setups."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=QDRANT_INSECURE_API_KEY_WARNING,
            category=UserWarning,
        )
        yield


# Read Only Mongo DB Configuration
READONLY_MONGO_USER = _getenv("READONLY_MONGO_USER", "")
READONLY_MONGO_PASSWORD = _getenv("READONLY_MONGO_PASSWORD", "")
READONLY_MONGO_HOST = _getenv("READONLY_MONGO_HOST", "localhost")
READONLY_MONGO_PORT = int(_getenv("READONLY_MONGO_PORT", "27017"))
READONLY_MONGO_DB_NAME = _getenv("READONLY_MONGO_DB_NAME", "WDA-Automan")


def _build_readonly_mongo_url() -> str:
    """Build MongoDB readonly URL from individual components."""
    if READONLY_MONGO_USER and READONLY_MONGO_PASSWORD:
        encoded_user = quote_plus(READONLY_MONGO_USER)
        encoded_password = quote_plus(READONLY_MONGO_PASSWORD)
        credentials = f"{encoded_user}:{encoded_password}"
        host_port = f"{READONLY_MONGO_HOST}:{READONLY_MONGO_PORT}"
        netloc = "@".join((credentials, host_port))
        return f"mongodb://{netloc}/?authSource={READONLY_MONGO_DB_NAME}"
    return f"mongodb://{READONLY_MONGO_HOST}:{READONLY_MONGO_PORT}"


_READONLY_MONGO_DB_URL_FROM_ENV = _getenv("READONLY_MONGO_DB_URL", "")
READONLY_MONGO_DB_URL = (
    _normalize_mongo_url(_READONLY_MONGO_DB_URL_FROM_ENV)
    if _READONLY_MONGO_DB_URL_FROM_ENV
    else _build_readonly_mongo_url()
)

# Write Mongo DB URL for Checkpointer
CHECKPOINTER_MONGO_DB_URL = _normalize_mongo_url(_getenv("CHECKPOINTER_MONGO_DB_URL"))


def _httpx_client(timeout: float = 10.0, cert_path: str | None = None) -> httpx.Client:
    verify: bool | str = True
    if cert_path and Path(cert_path).exists():
        verify = cert_path
    # Internal endpoints should not unexpectedly route through shell proxy env vars.
    return httpx.Client(
        timeout=timeout, verify=verify, trust_env=False, follow_redirects=True
    )


def get_memory_checkpointer():
    """Return in-memory checkpointer for quick local runs.- Volatile and is just for testing. Use MongoDBSaver for persistent checkpointer."""
    return MemorySaver()


def get_mongodb_checkpointer(mongo_db_url: str = CHECKPOINTER_MONGO_DB_URL):
    """Return MongoDBSaver context manager. Use with `with ... as checkpointer`. This is non-volatile and persists checkpoints to the specified MongoDB instance. Only checkpointer data will be saved."""

    if MongoDBSaver is None:
        raise ImportError(
            "MongoDB checkpointer requires 'langgraph.checkpoint.mongodb'. "
            "Install the package or use get_memory_checkpointer() for local runs."
        )

    @contextmanager
    def _open_with_fallback():
        checkpointer_mongo_db_url = _normalize_mongo_url(mongo_db_url)
        last_error = None
        try:
            with MongoDBSaver.from_conn_string(
                checkpointer_mongo_db_url
            ) as checkpointer:
                # Force a real server check while inside context.
                checkpointer.client.admin.command("ping")
                yield checkpointer
                return
        except (OSError, RuntimeError, ValueError) as e:
            last_error = e

        raise last_error

    return _open_with_fallback()


# 1) LLM model check connection
def check_llm_model_connection(
    model_name: str = MODEL_GPT_5,
    cert_path: str = DEFAULT_CERT_PATH,
    base_url: str = BASE_URL,
    api_key: str = OPENAI_API_KEY,
) -> tuple[bool, str]:
    """Check if LLM endpoint is reachable using a tiny invoke."""
    if not api_key:
        return False, "LLM api key is empty"
    if not base_url:
        return False, "LLM base URL is empty"

    llm = get_llm_model(
        model_name=model_name,
        temperature=0.7,
        cert_path=cert_path,
        base_url=base_url,
        api_key=api_key,
    )
    try:
        result = llm.invoke("ping")
        content = getattr(result, "content", "")
        return True, f"LLM reachable (sample={str(content)[:80]})"
    except (OSError, ValueError, RuntimeError) as e:
        return False, f"LLM connection failed: {type(e).__name__}: {e}"


# 2) LLM model
def get_llm_model(
    model_name: str = MODEL_GPT_5,
    temperature: float = 0.7,
    cert_path: str = DEFAULT_CERT_PATH,
    base_url: str = BASE_URL,
    api_key: str = OPENAI_API_KEY,
    **kwargs,
) -> ChatOpenAI:
    llm_http_client = _httpx_client(cert_path=cert_path, timeout=10.0)
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=llm_http_client,
        http_socket_options=(),
        model=model_name,
        temperature=temperature,
        **kwargs,
    )


def try_llm_invoke(llm: ChatOpenAI | None, prompt: str) -> str | None:
    """Invoke an LLM and return None on provider or transport failure."""
    if llm is None:
        return None
    try:
        result = llm.invoke(prompt)
        return getattr(result, "content", None)
    except (OpenAIError, OSError, RuntimeError, ValueError, AttributeError):
        return None


# 3a) LLM embedding model check connection
def check_llm_embedding_model_connection(
    model_name: str = TEXT_EMBEDDING,
    cert_path: str = DEFAULT_CERT_PATH,
    base_url: str = BASE_URL,
    api_key: str = OPENAI_API_KEY,
    check_ctx_length: bool = False,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
) -> tuple[bool, str]:
    """Check if embedding endpoint is reachable using a tiny embed query."""
    if not api_key:
        return False, "Embedding api key is empty"
    if not base_url:
        return False, "Embedding base URL is empty"

    embeddings_model = get_llm_embedding_model(
        model_name=model_name,
        cert_path=cert_path,
        base_url=base_url,
        api_key=api_key,
        dimensions=dimensions,
        check_ctx_length=check_ctx_length,
    )
    try:
        vector = embeddings_model.embed_query("ping")
        return True, f"Embedding reachable (dims={len(vector)})"
    except (OSError, ValueError, RuntimeError) as e:
        return False, f"Embedding connection failed: {type(e).__name__}: {e}"


# 3b) LLM embedding model
def get_llm_embedding_model(
    model_name: str = TEXT_EMBEDDING,
    cert_path: str = DEFAULT_CERT_PATH,
    base_url: str = BASE_URL,
    api_key: str = OPENAI_API_KEY,
    check_ctx_length: bool = False,
    dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
    **kwargs,
) -> OpenAIEmbeddings:
    embed_http_client = _httpx_client(cert_path=cert_path)
    return OpenAIEmbeddings(
        api_key=api_key,
        base_url=base_url,
        http_client=embed_http_client,
        model=model_name,
        # Disable local token checks by default to avoid external tokenizer fetches.
        check_embedding_ctx_length=check_ctx_length,
        tiktoken_enabled=False,
        dimensions=dimensions,
        **kwargs,
    )


def try_embed_query(embeddings_model: OpenAIEmbeddings | None, text: str) -> list[float] | None:
    """Embed a query and return None on provider or transport failure."""
    if embeddings_model is None:
        return None
    try:
        return embeddings_model.embed_query(text)
    except (OpenAIError, OSError, RuntimeError, ValueError, AttributeError):
        return None


# 4a) Langfuse check connection
def check_langfuse_connection(
    cert_path: str = DEFAULT_CERT_PATH,
    base_url: str = LANGFUSE_BASE_URL,
) -> tuple[bool, str]:
    """Check if Langfuse endpoint is reachable."""
    if not base_url:
        return False, "Langfuse base URL is empty"

    client = _httpx_client(timeout=5.0, cert_path=cert_path)
    try:
        response = client.get(base_url)
        return True, f"Langfuse reachable (status={response.status_code})"
    except (httpx.HTTPError, OSError) as e:
        return False, f"Langfuse connection failed: {type(e).__name__}: {e}"
    finally:
        client.close()


# 4b) Langfuse config creation
def get_langfuse_config(
    cert_path: str = DEFAULT_CERT_PATH,
    base_url: str = LANGFUSE_BASE_URL,
    public_key: str = LANGFUSE_PUBLIC_KEY,
    secret_key: str = LANGFUSE_SECRET_KEY,
) -> Langfuse | None:
    """Create and return Langfuse instance for tracing observability.
    Returns None if credentials missing or initialization fails (graceful fallback)."""
    if not (public_key and secret_key):
        logging.info("Langfuse credentials not configured, tracing disabled")
        return None

    try:
        langfuse_http_client = _httpx_client(cert_path=cert_path)
        langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            base_url=base_url,
            httpx_client=langfuse_http_client,
            should_export_span=lambda span: True,
        )
        logging.info("Langfuse initialized successfully")
        return langfuse
    except (OSError, RuntimeError, ValueError) as e:
        logging.warning(f"Langfuse initialization failed: {e}, continuing without tracing")
        return None


# 4c) Langfuse config builder for LangGraph invoke
def build_langfuse_config(
    user_id: str = "default-user",
    session_id: str = "default-session",
    thread_id: str = "default-thread",
    run_name: str = "analytica-run",
    tags: list[str] | None = None,
) -> dict:
    """Build LangGraph config dict with Langfuse observability integration.

    Includes configurable thread_id for checkpointing, callbacks, and metadata for tracing.
    Returns config dict ready for graph.invoke().
    """
    if tags is None:
        tags = ["analytica"]

    return {
        "configurable": {"thread_id": thread_id},
        "run_name": run_name,
        "tags": tags,
        "callbacks": [CallbackHandler()],
        "metadata": {
            "langfuse_user_id": user_id,
            "langfuse_session_id": session_id,
            "langfuse_thread_id": thread_id,
            "langfuse_tags": tags,
        },
    }


# 5) Check Qdrant Vector DB connection
def check_qdrant_connection(
    qdrant_url: str = QDRANT_VECTOR_DB_URL,
    qdrant_api_key: str = QDRANT_API_KEY,
) -> tuple[bool, str]:
    """Check if Qdrant endpoint is reachable."""
    if not qdrant_url:
        return False, "Qdrant URL not configured"

    try:
        with _suppress_qdrant_insecure_warning():
            client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key if qdrant_api_key else None,
                timeout=5.0,
            )
        client.get_collections()
        return True, f"Qdrant reachable (url={qdrant_url})"
    except (OSError, UnexpectedResponse) as e:
        return False, f"Qdrant connection failed: {type(e).__name__}: {str(e)[:100]}"


# 6) Connect with the Qdrant Vector DB and return a client instance
def get_qdrant_client(
    qdrant_url: str = QDRANT_VECTOR_DB_URL,
    qdrant_api_key: str = QDRANT_API_KEY,
    ensure_collection: bool = False,
    collection_name: str = QDRANT_SCHEMA_COLLECTION,
) -> QdrantClient:
    """Return a Qdrant client instance.

    If ensure_collection=True, creates the schema collection if it doesn't exist.
    Collection config: QDRANT_SCHEMA_COLLECTION with QDRANT_VECTOR_SIZE dims, COSINE distance.
    Raises exception if URL not configured or connection fails.
    """
    if not qdrant_url:
        raise ValueError("QDRANT_VECTOR_DB_URL not configured")

    with _suppress_qdrant_insecure_warning():
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key if qdrant_api_key else None,
            timeout=10.0,
            check_compatibility=False,  # Disable version compatibility check for flexibility
        )

    if ensure_collection:
        try:
            client.get_collection(collection_name)
        except UnexpectedResponse:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=QDRANT_VECTOR_SIZE,
                    distance=qmodels.Distance.COSINE
                ),
            )

    return client


# 7) Connect to Read Only MongoDB and return a client instance
def get_readonly_mongo_client(
    mongo_db_url: str | None = None,
) -> MongoClient:
    """Return a MongoDB client instance for read-only operations."""
    url = mongo_db_url or READONLY_MONGO_DB_URL
    return MongoClient(url)


def get_skills_from_mongodb(
    mongo_db_url: str = READONLY_MONGO_DB_URL,
    db_name: str = READONLY_MONGO_DB_NAME,
    collection_name: str = "skills",
) -> list[dict]:
    """Fetch skills from MongoDB collection. Returns list of skill dicts.

    Skills should have: name, collections, keywords, description, etc.
    Only returns enabled=True skills, sorted by priority.
    """
    try:
        client = get_readonly_mongo_client(mongo_db_url)
        db = client[db_name]
        skills_col = db[collection_name]
        skills = list(
            skills_col.find({"enabled": True}, {"_id": 0}).sort("priority", -1)
        )
        return skills
    except (OSError, RuntimeError, ValueError):
        return []


def check_runtime_connections(
    model_name: str = MODEL_GPT_5,
    cert_path: str = DEFAULT_CERT_PATH,
) -> dict[str, tuple[bool, str]]:
    """Check all runtime service connections: Langfuse, LLM, Embeddings, Qdrant."""
    return {
        "langfuse": check_langfuse_connection(cert_path=cert_path),
        "llm": check_llm_model_connection(model_name=model_name, cert_path=cert_path),
        "embedding": check_llm_embedding_model_connection(cert_path=cert_path),
        "qdrant": check_qdrant_connection(),
    }


if __name__ == "__main__":
    results = check_runtime_connections()
    for name, (ok, message) in results.items():
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {name}: {message}")
