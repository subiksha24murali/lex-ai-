import sqlite3

import bcrypt

from src.auth.db import get_connection


class EmailAlreadyExistsError(ValueError):
    """Raised when a user tries to register an existing email address."""


def _normalize_email(email):
    return email.strip().lower()


def _user_dict(row):
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"] if "role" in row.keys() else "citizen",
        "created_at": row["created_at"],
    }


def register_user(full_name, email, password, role="citizen"):
    normalized_email = _normalize_email(email)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (full_name.strip(), normalized_email, password_hash, role),
            )
    except sqlite3.IntegrityError as error:
        if "users.email" not in str(error):
            raise
        raise EmailAlreadyExistsError("An account with that email already exists.") from error


def authenticate_user(email, password):
    normalized_email = _normalize_email(email)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, full_name, email, password_hash, role, created_at FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()

    if row is None or not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return None
    return _user_dict(row)