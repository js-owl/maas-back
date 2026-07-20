"""Materials price sync: Bitrix CRM + Excel price lists → Postgres/Redis catalog."""

__all__ = ["run_materials_price_sync", "run_loop"]


def __getattr__(name: str):
    if name in ("run_materials_price_sync", "run_loop"):
        from backend.materials_price import sync as _sync

        return getattr(_sync, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
