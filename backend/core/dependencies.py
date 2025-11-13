"""
Core dependency injection functions
Used across multiple modules
Avoid importing auth dependencies here to prevent circular imports.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from fastapi import Request

# Prefer request-scoped DB session if available (set by middleware)
async def get_request_db(request: Request):
    db = getattr(request.state, "db", None)
    if db is not None:
        return db
    # Fallback to global dependency
    async for session in get_db():
        return session

# Re-export for convenience
__all__ = ["get_db", "get_request_db"]

