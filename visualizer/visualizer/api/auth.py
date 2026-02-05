"""API key authentication and tenant resolution."""

import os
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from visualizer.infra.context import get_tenant_by_api_key

security = HTTPBearer()

DB_PATH = Path(os.getenv("DB_PATH", "/data/pipelines"))


def resolve_org(api_key: str) -> tuple[str, Path]:
    """
    Resolve an API key to a tenant slug and its pipeline database path.

    Returns:
        Tuple of (tenant_slug, db_path)

    Raises:
        HTTPException: If API key is invalid
    """
    tenant = get_tenant_by_api_key(api_key)
    if tenant is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    db_path = DB_PATH / tenant.db_name
    return tenant.slug, db_path


async def get_org_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> tuple[str, Path]:
    """Dependency that validates API key and returns org context."""
    return resolve_org(credentials.credentials)
