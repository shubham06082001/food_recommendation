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


INGREDIENTS = "ecos_ingredients"


def ingredient_scores(query: str, ingredients: dict[str, str]) -> dict[str, float]:
    """Qdrant similarity of a free-text query (e.g. 'dairy', 'leafy greens') to ingredient descriptions.

    Vectors live in their own collection, keyed by the description, so new or re-categorised items are re-embedded.
    """
    if not query.strip() or not ingredients:
        return {}
    try:
        from uuid import NAMESPACE_URL, uuid5

        from qdrant_client.http import models
        from utilities import embed_texts, try_embed_local_query

        client, model = _resources()
        if not client.collection_exists(INGREDIENTS):
            client.create_collection(INGREDIENTS, vectors_config=models.VectorParams(
                size=256, distance=models.Distance.COSINE))
        ids = {key: str(uuid5(NAMESPACE_URL, f"ecos:{key}:{name.lower()}")) for key, name in ingredients.items()}
        known = {p.id for p in client.retrieve(INGREDIENTS, ids=list(ids.values()))}
        missing = [key for key, point_id in ids.items() if point_id not in known]
        if missing:
            vectors = embed_texts(model, [ingredients[k] for k in missing], dimensions=256)
            client.upsert(INGREDIENTS, points=[
                models.PointStruct(id=ids[k], vector=v.tolist(), payload={"ingredient_id": k, "name": ingredients[k]})
                for k, v in zip(missing, vectors)])
        response = client.query_points(
            INGREDIENTS, query=try_embed_local_query(model, query, dimensions=256).tolist(),
            query_filter=models.Filter(must=[models.HasIdCondition(has_id=list(ids.values()))]),
            limit=len(ids), with_payload=["ingredient_id"])
        return {p.payload["ingredient_id"]: round(float(p.score), 3) for p in response.points}
    except Exception as error:  # Optional: callers fall back to name matching.
        logger.warning("Ingredient semantic search unavailable: %s", error)
        return {}
