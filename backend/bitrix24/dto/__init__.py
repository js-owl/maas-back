"""DTOs and base utilities for Bitrix24 entities.

Helpers:
- dump_exclude_none(obj): Pydantic model_dump with exclude_none=True for request payloads.
- from_result(model_class, data): model_validate for API result (single or list).
"""

from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def dump_exclude_none(obj: BaseModel) -> dict[str, Any]:
    """Serialize a Pydantic model to dict, excluding None values (for Bitrix24 request payloads)."""
    return obj.model_dump(exclude_none=True)


def from_result(model_class: type[T], data: Any) -> T | list[T]:
    """Parse API result into model instance or list of model instances."""
    if isinstance(data, list):
        return [model_class.model_validate(item) for item in data]
    return model_class.model_validate(data)
