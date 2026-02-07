"""Ingest business logic - API key resolution."""

import logging
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings
from lib.ctx.identity import get_tenant_by_api_key

logger = logging.getLogger(__name__)

security = HTTPBearer()
require_bearer = Depends(security)


def resolve_org(api_key: str) -> tuple[str, Path]:
    """Resolve an API key to a tenant slug and its pipeline database path."""
    tenant = get_tenant_by_api_key(api_key)

    if tenant is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    db_path = settings.default_db_path / tenant.db_name
    return tenant.slug, db_path


async def get_org_context(
    credentials: HTTPAuthorizationCredentials = require_bearer,
) -> tuple[str, Path]:
    """Dependency that validates API key and returns org context."""
    return resolve_org(credentials.credentials)
