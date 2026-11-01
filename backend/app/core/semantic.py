import logging
from functools import lru_cache

logger = logging.getLogger(__name__)
COLLECTION = "food_nutrients"


@lru_cache(maxsize=1)
def _resources():
    from utilities import get_embedding_model, get_qdrant_client

    return get_qdrant_client(), get_embedding_model("all-MiniLM-L6-v2")


def semantic_scores(query: str, food_codes: list[str]) -> dict[str, float]:
    """Qdrant similarity per food_code; empty when Qdrant or the model is unavailable."""
    if not query.strip() or not food_codes:
        return {}
    try:
        from qdrant_client.http import models
        from utilities import try_embed_local_query

        client, model = _resources()
        vector = try_embed_local_query(model, query, dimensions=256)
        response = client.query_points(
            collection_name=COLLECTION,
            query=vector.tolist(),
            query_filter=models.Filter(
                must=[models.FieldCondition(key="food_code", match=models.MatchAny(any=food_codes))]
            ),
            limit=len(food_codes),
            with_payload=["food_code"],
        )
        return {p.payload["food_code"]: round(float(p.score), 3) for p in response.points}
    except Exception as error:  # Qdrant is optional; ranking falls back to goal rules.
        logger.warning("Semantic ranking unavailable: %s", error)
        return {}
