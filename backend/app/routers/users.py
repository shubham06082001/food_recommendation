from datetime import timedelta
from secrets import token_urlsafe
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from ..core.common import current_user, now_utc, require_self_or_manager, serialize
from ..core.database import get_db

router = APIRouter()

SESSION_MINUTES = 30

Diet = Literal["vegetarian", "vegan", "eggetarian", "non_vegetarian", "no_preference"]
Goal = Literal["high_protein", "high_fibre", "lower_sodium", "balanced"]


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")


class PreferencesRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    dietary_preference: Diet = "no_preference"
    wellness_goals: list[Goal] = Field(default_factory=list)
    declared_allergens: list[str] = Field(default_factory=list)
    favourite_categories: list[str] = Field(default_factory=list)
    consented: bool


def _profile(user: dict) -> dict:
    role = user.get("role", "employee")
    return {"user_id": user["user_id"], "name": user.get("name", user["user_id"]), "role": role,
            "profile_complete": bool(user.get("profile_complete")),
            "next_screen": "manager_home" if role == "manager" else "employee_home"}


@router.post("/auth/login")
def login(payload: LoginRequest, db: Any = Depends(get_db)) -> dict:
    user_id = payload.user_id.strip().upper()
    user = db.users.find_one({"user_id": user_id})
    if user is None:
        # Unknown IDs only ever become employees; managers are seeded.
        user = {"user_id": user_id, "name": f"Employee {user_id}", "role": "employee",
                "preferences": {}, "profile_complete": False, "created_at": now_utc()}
        db.users.insert_one(user)
    token = token_urlsafe(32)
    expires = now_utc() + timedelta(minutes=SESSION_MINUTES)
    db.sessions.insert_one({"token": token, "user_id": user_id, "created_at": now_utc(), "expires_at": expires})
    return {**_profile(user), "session_token": token, "expires_at": expires.isoformat(),
            "session_minutes": SESSION_MINUTES}


@router.get("/auth/session")
def refresh_session(x_session_token: str = Header(min_length=20, max_length=100), db: Any = Depends(get_db)) -> dict:
    """Validate a browser session and slide its expiry 30 minutes forward (activity keeps it alive)."""
    expires = now_utc() + timedelta(minutes=SESSION_MINUTES)
    session = db.sessions.find_one_and_update({"token": x_session_token, "expires_at": {"$gt": now_utc()}},
                                              {"$set": {"expires_at": expires, "last_seen": now_utc()}})
    user = db.users.find_one({"user_id": session["user_id"]}) if session else None
    if not user:
        raise HTTPException(status_code=401, detail="Session expired; please log in again")
    return {**_profile(user), "expires_at": expires.isoformat(), "session_minutes": SESSION_MINUTES}


@router.post("/auth/logout")
def logout(x_session_token: str = Header(default=""), db: Any = Depends(get_db)) -> dict:
    db.sessions.delete_one({"token": x_session_token})
    return {"success": True}


@router.get("/users/{user_id}")
def get_user(user_id: str, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    require_self_or_manager(user_id, user)
    found = db.users.find_one({"user_id": user_id})
    if not found:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize(found)


@router.put("/users/{user_id}/preferences")
def save_preferences(
    user_id: str, payload: PreferencesRequest,
    user: dict = Depends(current_user), db: Any = Depends(get_db),
) -> dict:
    if user["user_id"] != user_id or user.get("role") != "employee":
        raise HTTPException(status_code=403, detail="Employees can only update their own preferences")
    if not payload.consented:
        raise HTTPException(status_code=400, detail="Consent is required to save preferences")
    preferences = payload.model_dump(exclude={"name"})
    preferences["declared_allergens"] = sorted({a.strip().lower() for a in payload.declared_allergens if a.strip()})
    update = {"preferences": preferences, "profile_complete": True, "updated_at": now_utc()}
    if payload.name:
        update["name"] = payload.name.strip()
    db.users.update_one({"user_id": user_id}, {"$set": update})
    return {"success": True, "profile_complete": True, "preferences": preferences}


@router.get("/users")
def list_users(db: Any = Depends(get_db)) -> dict:
    fields = {"_id": 0, "user_id": 1, "name": 1, "role": 1, "profile_complete": 1}
    return {"success": True, "data": list(db.users.find({}, fields).sort("user_id", 1))}
