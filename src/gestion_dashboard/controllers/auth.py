"""User authentication and account management.

Users are stored globally in ``data/users.parquet``.
Each user's budget data lives in its own subdirectory ``data/user_<id>/``.
Passwords are hashed with PBKDF2-HMAC-SHA256 + 16-byte random salt.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import os
import re
from typing import Optional

import pandas as pd

from gestion_dashboard.models.budget import User

# Users table lives at the root of the data directory (not per-user)
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PKG_ROOT, "data")
_USERS_PATH = os.path.join(_DATA_DIR, "users.parquet")

_USERS_SCHEMA: dict = {
    "id": [], "username": [], "display_name": [],
    "password_hash": [], "created_at": [], "last_login": [], "is_active": [],
}

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")

# PBKDF2 iteration count (high enough for security, fast enough for UX)
_PBKDF2_ITERATIONS = 260_000


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _load_users() -> pd.DataFrame:
    os.makedirs(_DATA_DIR, exist_ok=True)
    if os.path.exists(_USERS_PATH):
        try:
            return pd.read_parquet(_USERS_PATH)
        except Exception:
            pass
    return pd.DataFrame(_USERS_SCHEMA)


def _save_users(df: pd.DataFrame) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    df.to_parquet(_USERS_PATH, index=False)


def _hash_password(password: str) -> str:
    """Return a base64-encoded `salt || PBKDF2-derived key` string."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return base64.b64encode(salt + key).decode()


def _verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time password comparison using hmac.compare_digest."""
    try:
        data = base64.b64decode(stored_hash.encode())
        salt, stored_key = data[:16], data[16:]
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(stored_key, candidate)
    except Exception:
        return False


def _row_to_user(row: dict) -> User:
    row = dict(row)
    row["is_active"] = bool(row.get("is_active", True))
    for field in ("display_name", "last_login"):
        if row.get(field) != row.get(field):  # NaN guard
            row[field] = ""
    return User(**row)


# ─── Public API ───────────────────────────────────────────────────────────────

def has_any_user() -> bool:
    """Return True if at least one account exists."""
    df = _load_users()
    return not df.empty


def username_exists(username: str) -> bool:
    df = _load_users()
    return (
        not df.empty
        and username.lower().strip() in df["username"].str.lower().values
    )


def register_user(
    username: str,
    password: str,
    display_name: str = "",
    password_confirm: str = "",
) -> tuple[Optional[User], str]:
    """
    Register a new user.

    Returns
    -------
    (User, "")
        On success.
    (None, error_message)
        On validation failure.
    """
    username = username.strip()
    display_name = display_name.strip()
    password_confirm = password_confirm.strip()

    if not username:
        return None, "Le nom d'utilisateur est requis."
    if not _USERNAME_RE.match(username):
        return None, (
            "Le nom d'utilisateur doit contenir 3 à 20 caractères "
            "alphanumériques ou underscores."
        )
    if len(password) < 6:
        return None, "Le mot de passe doit contenir au moins 6 caractères."
    if password_confirm and password != password_confirm:
        return None, "Les mots de passe ne correspondent pas."
    if username_exists(username):
        return None, "Ce nom d'utilisateur est déjà pris."

    df = _load_users()
    new_id = int(df["id"].max()) + 1 if not df.empty else 1
    now = datetime.datetime.now().isoformat()

    user = User(
        id=new_id,
        username=username.lower(),
        display_name=display_name or username,
        password_hash=_hash_password(password),
        created_at=now,
        last_login=now,
        is_active=True,
    )
    df = pd.concat([df, pd.DataFrame([user.model_dump()])], ignore_index=True)
    _save_users(df)

    # Create the user-specific data directory eagerly
    os.makedirs(get_user_data_dir(user.id), exist_ok=True)
    return user, ""


def authenticate(username: str, password: str) -> tuple[Optional[User], str]:
    """
    Verify credentials.

    Returns
    -------
    (User, "")
        On success.
    (None, error_message)
        On failure.
    """
    df = _load_users()
    if df.empty:
        return None, "Aucun compte enregistré."

    match = df[df["username"].str.lower() == username.lower().strip()]
    if match.empty:
        # Constant-time guard: avoid revealing which usernames exist
        _verify_password(password, _hash_password("__dummy__"))
        return None, "Identifiants incorrects."

    user = _row_to_user(match.iloc[0].to_dict())
    if not user.is_active:
        return None, "Ce compte est désactivé."
    if not _verify_password(password, user.password_hash):
        return None, "Identifiants incorrects."

    # Update last_login
    now = datetime.datetime.now().isoformat()
    df.loc[df["id"] == user.id, "last_login"] = now
    _save_users(df)
    user.last_login = now
    return user, ""


def change_password(
    user_id: int,
    old_password: str,
    new_password: str,
) -> tuple[bool, str]:
    """Change a user's password after verifying the old one."""
    df = _load_users()
    match = df[df["id"] == user_id]
    if match.empty:
        return False, "Utilisateur introuvable."
    user = _row_to_user(match.iloc[0].to_dict())
    if not _verify_password(old_password, user.password_hash):
        return False, "Mot de passe actuel incorrect."
    if len(new_password) < 6:
        return False, "Le nouveau mot de passe doit contenir au moins 6 caractères."
    df.loc[df["id"] == user_id, "password_hash"] = _hash_password(new_password)
    _save_users(df)
    return True, ""


def get_all_users() -> list[User]:
    """Return all registered users."""
    return [_row_to_user(r) for r in _load_users().to_dict("records")]


def get_user_data_dir(user_id: int) -> str:
    """Return the data directory path for a specific user."""
    return os.path.join(_DATA_DIR, f"user_{user_id}")
