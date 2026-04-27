import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(seconds=settings.jwt_access_token_expire)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """Return (raw_token, hashed_token). Store only the hash in DB."""
    raw = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict:
    """Raise JWTError on invalid/expired token."""
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload
