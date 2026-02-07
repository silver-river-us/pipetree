from pathlib import Path

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lib.ctx.identity import resolve_org
from lib.exceptions import InvalidApiKeyError
from lib.security import decode_token

security = HTTPBearer()
require_bearer = Depends(security)


def get_current_user(request: Request) -> dict | None:
    """Get the current user from the session cookie."""
    token = request.cookies.get("session")
    if not token:
        return None
    return decode_token(token)


def get_db_path(db: str | None, request: Request | None = None) -> Path:
    """Get database path from explicit param or logged-in tenant."""
    from lib.ctx.identity import get_tenant

    from config import settings

    if db:
        return Path(db)
    if request:
        user = get_current_user(request)
        if user and user.get("tenant_id"):
            tenant = get_tenant(user["tenant_id"])
            if tenant:
                return settings.default_db_path / tenant.db_name
    return settings.default_db_path


def get_template_context(db_path: Path) -> dict:
    """Get common template context."""
    return {
        "databases": [],
        "current_db": str(db_path),
    }


def require_login(request: Request) -> RedirectResponse | None:
    """Return redirect response if not authenticated, else None."""
    user = get_current_user(request)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return None


async def get_org_context(
    credentials: HTTPAuthorizationCredentials = require_bearer,
) -> tuple[str, Path]:
    """Dependency that validates API key and returns org context."""

    try:
        return resolve_org(credentials.credentials)
    except InvalidApiKeyError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e
