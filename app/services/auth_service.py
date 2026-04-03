import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.database import get_connection


SESSION_DURATION_DAYS = 30


def _utc_now():
    return datetime.now(timezone.utc)


def _utc_now_string():
    return _utc_now().isoformat(timespec="seconds")


def _normalize_email(email: str):
    return email.strip().lower()


def _hash_password(password: str, salt: bytes | None = None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str):
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
    except ValueError:
        return False

    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return hmac.compare_digest(candidate, expected)


def _user_payload(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


def register_user(name: str | None, email: str, password: str):
    normalized_email = _normalize_email(email)
    user_id = str(uuid4())

    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
        if existing:
            raise ValueError("An account with this email already exists.")

        connection.execute(
            """
            INSERT INTO users (id, name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name.strip() if name else None,
                normalized_email,
                _hash_password(password),
                _utc_now_string(),
            ),
        )

        row = connection.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    return _user_payload(row)


def authenticate_user(email: str, password: str):
    normalized_email = _normalize_email(email)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()

    if row is None or not _verify_password(password, row["password_hash"]):
        raise ValueError("Invalid email or password.")

    return _user_payload(row)


def create_session(user_id: str):
    token = secrets.token_urlsafe(32)
    created_at = _utc_now()
    expires_at = created_at + timedelta(days=SESSION_DURATION_DAYS)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO auth_sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                token,
                user_id,
                created_at.isoformat(timespec="seconds"),
                expires_at.isoformat(timespec="seconds"),
            ),
        )

    return token


def get_user_from_token(token: str):
    if not token:
        return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.name, users.email, users.created_at, auth_sessions.expires_at
            FROM auth_sessions
            JOIN users ON users.id = auth_sessions.user_id
            WHERE auth_sessions.token = ?
            """,
            (token,),
        ).fetchone()

    if row is None:
        return None

    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at <= _utc_now():
        revoke_session(token)
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


def revoke_session(token: str):
    with get_connection() as connection:
        connection.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
