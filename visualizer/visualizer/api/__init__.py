"""REST Ingest API for receiving pipeline progress data from remote workers."""

from .router import router

__all__ = ["router"]
