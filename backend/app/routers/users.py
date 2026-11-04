from datetime import timedelta
from secrets import token_urlsafe
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from ..core.common import current_user, now_utc, require_manager, require_self_or_manager, serialize
from ..core.database import get_db
from ..core.security import hash_password, token_digest, verify_password

router = APIRouter()

SESSION_MINUTES = 30
MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 5

Diet = Literal["vegetarian", "vegan", "eggetarian", "non_vegetarian", "no_preference"]
Goal = Literal["high_protein", "high_fibre", "lower_sodium", "balanced"]


class LoginRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)


class PreferencesRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    dietary_preference: Diet = "no_preference"
    wellness_goals: list[Goal] = Field(default_factory=list, max_length=4)
    declared_allergens: list[str] = Field(default_factory=list, max_length=20)
    favourite_categories: list[str] = Field(default_factory=list, max_length=20)
    consented: bool


def _profile(user: dict) -> dict:
    role = user.get("role", "employee")
    return {"user_id": user["user_id"], "name": user.get("name", user["user_id"]), "role": role,
            "profile_complete": bool(user.get("profile_complete")),
            "next_screen": "manager_home" if role == "manager" else "employee_home"}


def _bad_credentials() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid user ID or password")


def _authenticate(db: Any, user_id: str, password: str) -> dict:
    """Existing users must match their password; an unknown ID registers a new employee with this password."""
    user = db.users.find_one({"user_id": user_id})
    if user is None:
        user = {"user_id": user_id, "name": f"Employee {user_id}", "role": "employee", "preferences": {},
                "profile_complete": False, "created_at": now_utc(), "password_hash": hash_password(password)}
        try:
            db.users.insert_one(user)
        except DuplicateKeyError as error:  # Two first logins raced; the loser must now prove the password.
            raise _bad_credentials() from error
        return user
    if (user.get("locked_until") or now_utc()) > now_utc():
        raise HTTPException(status_code=429, detail=f"Too many failed attempts; try again in {LOCK_MINUTES} minutes")
    if not user.get("password_hash"):
        if user.get("role") == "manager":  # Managers are provisioned from the environment only.
            raise _bad_credentials()
        db.users.update_one({"user_id": user_id}, {"$set": {"password_hash": hash_password(password)}})
    elif not verify_password(password, user["password_hash"]):
        failed = user.get("failed_logins", 0) + 1
        locked = failed >= MAX_FAILED_LOGINS
        db.users.update_one({"user_id": user_id}, {"$set": {
            "failed_logins": 0 if locked else failed,
            **({"locked_until": now_utc() + timedelta(minutes=LOCK_MINUTES)} if locked else {})}})
        raise _bad_credentials()
    db.users.update_one({"user_id": user_id}, {"$set": {"failed_logins": 0}, "$unset": {"locked_until": ""}})
    return user


@router.post("/auth/login")
def login(payload: LoginRequest, db: Any = Depends(get_db)) -> dict:
    user_id = payload.user_id.strip().upper()
    user = _authenticate(db, user_id, payload.password)
    token = token_urlsafe(32)
    expires = now_utc() + timedelta(minutes=SESSION_MINUTES)
    db.sessions.insert_one({"token_hash": token_digest(token), "user_id": user_id, "created_at": now_utc(),
                            "expires_at": expires})
    return {**_profile(user), "session_token": token, "expires_at": expires.isoformat(),
            "session_minutes": SESSION_MINUTES}


@router.get("/auth/session")
def refresh_session(x_session_token: str = Header(min_length=20, max_length=100), db: Any = Depends(get_db)) -> dict:
    """Validate a browser session and slide its expiry 30 minutes forward (activity keeps it alive)."""
    expires = now_utc() + timedelta(minutes=SESSION_MINUTES)
    session = db.sessions.find_one_and_update({"token_hash": token_digest(x_session_token), "expires_at": {"$gt": now_utc()}},
                                              {"$set": {"expires_at": expires, "last_seen": now_utc()}})
    user = db.users.find_one({"user_id": session["user_id"]}) if session else None
    if not user:
        raise HTTPException(status_code=401, detail="Session expired; please log in again")
    return {**_profile(user), "expires_at": expires.isoformat(), "session_minutes": SESSION_MINUTES}


@router.post("/auth/logout")
def logout(x_session_token: str = Header(default=""), db: Any = Depends(get_db)) -> dict:
    db.sessions.delete_one({"token_hash": token_digest(x_session_token)})
    return {"success": True}


@router.get("/users/{user_id}")
def get_user(user_id: str, user: dict = Depends(current_user), db: Any = Depends(get_db)) -> dict:
    require_self_or_manager(user_id, user)
    found = db.users.find_one({"user_id": user_id}, {"password_hash": 0, "failed_logins": 0, "locked_until": 0})
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
    preferences["declared_allergens"] = sorted({a.strip().lower()[:40] for a in payload.declared_allergens if a.strip()})
    update = {"preferences": preferences, "profile_complete": True, "updated_at": now_utc()}
    if payload.name:
        update["name"] = payload.name.strip()
    db.users.update_one({"user_id": user_id}, {"$set": update})
    return {"success": True, "profile_complete": True, "preferences": preferences}


@router.get("/users")
def list_users(_: dict = Depends(require_manager), db: Any = Depends(get_db)) -> dict:
    fields = {"_id": 0, "user_id": 1, "name": 1, "role": 1, "profile_complete": 1}
    return {"success": True, "data": list(db.users.find({}, fields).sort("user_id", 1))}
