"""
Prometheus HTTP metrics grouped by OpenAPI domain tag (api_group).
"""
from __future__ import annotations

import time
from typing import FrozenSet

from fastapi import FastAPI, Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

EXCLUDED_PATHS: FrozenSet[str] = frozenset({
    "/metrics",
    "/health",
    "/health/detailed",
    "/docs",
    "/redoc",
    "/openapi.json",
})

TAG_TO_GROUP: dict[str, str] = {
    "Authentication": "auth",
    "Users": "users",
    "Orders": "orders",
    "Files": "files",
    "Preview": "files",
    "Calculation": "calculation",
    "Services": "calculation",
    "Calculator": "calculation",
    "Basket": "basket",
    "Kits": "kits",
    "Documents": "documents",
    "Invoices": "invoices",
    "Call Requests": "call_requests",
    "Admin": "admin",
    "External API": "external",
    "System": "system",
    "Root": "system",
    "Debug": "system",
}

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "api_group", "status"],
)

HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "api_group"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)


def resolve_api_group(request: Request) -> str:
    route = request.scope.get("route")
    if route is None:
        return "other"

    tags = list(getattr(route, "tags", None) or [])
    for tag in tags:
        group = TAG_TO_GROUP.get(tag)
        if group and group != "admin":
            return group
    for tag in tags:
        group = TAG_TO_GROUP.get(tag)
        if group:
            return group
    if tags:
        return tags[0].lower().replace(" ", "_")
    return "other"


def _should_track(path: str) -> bool:
    return path not in EXCLUDED_PATHS


def setup_prometheus(app: FastAPI) -> None:
    @app.middleware("http")
    async def prometheus_middleware(request: Request, call_next):
        path = request.url.path
        if not _should_track(path):
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start
            api_group = resolve_api_group(request)
            method = request.method
            HTTP_REQUESTS.labels(
                method=method,
                api_group=api_group,
                status=str(status_code),
            ).inc()
            HTTP_DURATION.labels(method=method, api_group=api_group).observe(duration)

    @app.get("/metrics", include_in_schema=False, tags=["System"])
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
