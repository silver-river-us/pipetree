"""Databases API controller."""

import json
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from config import DATABASES_CONFIG_PATH, PROJECT_ROOT

from .input_objects.ingest import AddDatabaseRequest

router = APIRouter(prefix="/databases")


def _load_databases() -> list[dict]:
    """Load the list of configured databases."""
    if DATABASES_CONFIG_PATH.exists():
        with open(DATABASES_CONFIG_PATH) as f:
            config = json.load(f)
            databases = config.get("databases", [])

            for db in databases:
                db_path = Path(db["path"])

                if not db_path.is_absolute():
                    db["path"] = str(PROJECT_ROOT / db_path)

                db["exists"] = Path(db["path"]).exists()

            return databases

    return []


def _save_databases(databases: list[dict]) -> None:
    """Save the list of configured databases."""
    save_data = []

    for db in databases:
        db_path = Path(db["path"])

        try:
            relative_path = db_path.relative_to(PROJECT_ROOT)
            save_data.append({"name": db["name"], "path": str(relative_path)})
        except ValueError:
            save_data.append({"name": db["name"], "path": str(db_path)})

    with open(DATABASES_CONFIG_PATH, "w") as f:
        json.dump({"databases": save_data}, f, indent=2)


@router.get("")
async def list_databases():
    """Get list of configured databases."""
    return JSONResponse(content={"databases": _load_databases()})


@router.post("")
async def create_database(data: AddDatabaseRequest):
    """Add a new database to the configuration."""
    databases = _load_databases()
    new_db = {"name": data.name, "path": data.path, "exists": Path(data.path).exists()}
    databases.append(new_db)
    _save_databases(databases)
    return JSONResponse(content={"database": new_db})


@router.delete("")
async def delete_database(path: str = Query(...)):
    """Remove a database from the configuration."""
    databases = _load_databases()
    original_len = len(databases)
    databases = [db for db in databases if db["path"] != path]

    if len(databases) < original_len:
        _save_databases(databases)
        return JSONResponse(content={"success": True})

    return JSONResponse(content={"success": False})
