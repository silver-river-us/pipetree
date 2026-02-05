"""API key authentication and organization resolution."""

import json
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

# Organizations config is stored on the volume alongside databases
ORGS_CONFIG_PATH = Path(os.getenv("DB_PATH", "/data/pipelines")) / "organizations.json"


def load_organizations() -> dict[str, Any]:
    """Load organizations config from volume."""
    if ORGS_CONFIG_PATH.exists():
        with open(ORGS_CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_organizations(orgs: dict[str, Any]) -> None:
    """Save organizations config to volume."""
    ORGS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ORGS_CONFIG_PATH, "w") as f:
        json.dump(orgs, f, indent=2)


def resolve_org(api_key: str) -> tuple[str, Path]:
    """
    Resolve an API key to an organization name and its database path.

    Returns:
        Tuple of (org_name, db_path)

    Raises:
        HTTPException: If API key is invalid
    """
    orgs = load_organizations()
    for org_name, org_config in orgs.items():
        if org_config.get("api_key") == api_key:
            db_dir = Path(os.getenv("DB_PATH", "/data/pipelines"))
            db_path = db_dir / org_config.get("db", f"{org_name}.db")
            return org_name, db_path

    raise HTTPException(status_code=401, detail="Invalid API key")


async def get_org_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> tuple[str, Path]:
    """Dependency that validates API key and returns org context."""
    return resolve_org(credentials.credentials)
