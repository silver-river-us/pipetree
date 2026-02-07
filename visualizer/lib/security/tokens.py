from datetime import UTC, datetime, timedelta

import jwt

from config import settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def encode_token(user_id: str, email: str, tenant_id: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "tenant_id": tenant_id,
        "exp": datetime.now(UTC).replace(tzinfo=None)
        + timedelta(hours=JWT_EXPIRE_HOURS),
    }

    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
