import logging
from uuid import NAMESPACE_URL, uuid5

from qdrant_client.http import models

from . import vectors

logger = logging.getLogger(__name__)
COLLECTION = "food_nutrients"
INGREDIENTS = "ecos_ingredients"


def semantic_scores(query: str, food_codes: list[str]) -> dict[str, float]:
    """Qdrant similarity per food_code; empty when Qdrant or the model is unavailable."""
    if not query.strip() or not food_codes or vectors.cooling_down():
        return {}
    if not vectors.ready():
        vectors.start_warm_up()  # Never block the request on a model load.
        return {}
    try:
        response = vectors.qdrant().query_points(
            collection_name=COLLECTION,
            query=vectors.embed_query(query.strip()),
            query_filter=models.Filter(must=[models.FieldCondition(key="food_code",
                                                                   match=models.MatchAny(any=food_codes))]),
            limit=len(food_codes), with_payload=["food_code"])
        return {p.payload["food_code"]: round(float(p.score), 3) for p in response.points}
    except Exception as error:  # Qdrant is optional; ranking falls back to goal rules.
        logger.warning("Semantic ranking unavailable: %s", error)
        vectors.cool_down()
        return {}


def ingredient_scores(query: str, ingredients: dict[str, str]) -> dict[str, float]:
    """Qdrant similarity of a free-text query (e.g. 'dairy', 'leafy greens') to ingredient names.

    Vectors live in their own collection, keyed by the name, so new or re-categorised items are re-embedded.
    """
    if not query.strip() or not ingredients or vectors.cooling_down():
        return {}
    if not vectors.ready():
        vectors.start_warm_up()
        return {}
    try:
        client = vectors.qdrant()
        if not client.collection_exists(INGREDIENTS):
            client.create_collection(INGREDIENTS, vectors_config=models.VectorParams(
                size=vectors.DIMENSIONS, distance=models.Distance.COSINE))
        ids = {key: str(uuid5(NAMESPACE_URL, f"ecos:{key}:{name.lower()}")) for key, name in ingredients.items()}
        known = {p.id for p in client.retrieve(INGREDIENTS, ids=list(ids.values()))}
        missing = [key for key, point_id in ids.items() if point_id not in known]
        if missing:
            client.upsert(INGREDIENTS, points=[
                models.PointStruct(id=ids[k], vector=v.tolist(), payload={"ingredient_id": k, "name": ingredients[k]})
                for k, v in zip(missing, vectors.embed([ingredients[k] for k in missing]))])
        response = client.query_points(
            INGREDIENTS, query=vectors.embed_query(query.strip()),
            query_filter=models.Filter(must=[models.HasIdCondition(has_id=list(ids.values()))]),
            limit=len(ids), with_payload=["ingredient_id"])
        return {p.payload["ingredient_id"]: round(float(p.score), 3) for p in response.points}
    except Exception as error:  # Optional: callers fall back to name matching.
        logger.warning("Ingredient semantic search unavailable: %s", error)
        vectors.cool_down()
        return {}
