"""Activity DTOs for crm.activity.* methods."""

from typing import Any

from pydantic import BaseModel


class ActivityCommunication(BaseModel):
    """Row in COMMUNICATIONS (crm_activity_communication)."""

    ID: int | None = None
    ACTIVITY_ID: int | None = None
    ENTITY_ID: int | None = None
    ENTITY_TYPE_ID: int | None = None
    TYPE: str | None = None
    VALUE: str | None = None

    model_config = {"extra": "allow"}


class ActivityCreate(BaseModel):
    """Fields for creating an activity (crm.activity.add)."""

    OWNER_ID: int | None = None
    OWNER_TYPE_ID: int | None = None
    TYPE_ID: str | None = None
    PROVIDER_ID: str | None = None
    PROVIDER_TYPE_ID: str | None = None
    PROVIDER_GROUP_ID: str | None = None
    SUBJECT: str | None = None
    START_TIME: str | None = None
    END_TIME: str | None = None
    DEADLINE: str | None = None
    COMPLETED: str | None = None
    STATUS: str | None = None
    RESPONSIBLE_ID: int | None = None
    PRIORITY: str | None = None
    NOTIFY_TYPE: str | None = None
    NOTIFY_VALUE: int | None = None
    DESCRIPTION: str | None = None
    DESCRIPTION_TYPE: str | None = None
    DIRECTION: str | None = None
    LOCATION: str | None = None
    SETTINGS: dict[str, Any] | None = None
    ORIGIN_ID: str | None = None
    ORIGINATOR_ID: str | None = None
    RESULT_STATUS: int | None = None
    RESULT_STREAM: int | None = None
    RESULT_SOURCE_ID: str | None = None
    PROVIDER_PARAMS: dict[str, Any] | None = None
    PROVIDER_DATA: str | None = None
    RESULT_MARK: int | None = None
    RESULT_VALUE: float | None = None
    RESULT_SUM: float | None = None
    RESULT_CURRENCY_ID: str | None = None
    AUTOCOMPLETE_RULE: int | None = None
    COMMUNICATIONS: list[ActivityCommunication] | None = None
    FILES: list[dict[str, Any]] | None = None
    WEBDAV_ELEMENTS: list[dict[str, Any]] | None = None

    model_config = {"extra": "allow"}


class ActivityUpdate(BaseModel):
    """Fields for updating an activity."""

    OWNER_ID: int | None = None
    OWNER_TYPE_ID: int | None = None
    TYPE_ID: str | None = None
    PROVIDER_ID: str | None = None
    PROVIDER_TYPE_ID: str | None = None
    PROVIDER_GROUP_ID: str | None = None
    SUBJECT: str | None = None
    START_TIME: str | None = None
    END_TIME: str | None = None
    DEADLINE: str | None = None
    COMPLETED: str | None = None
    STATUS: str | None = None
    RESPONSIBLE_ID: int | None = None
    PRIORITY: str | None = None
    NOTIFY_TYPE: str | None = None
    NOTIFY_VALUE: int | None = None
    DESCRIPTION: str | None = None
    DESCRIPTION_TYPE: str | None = None
    DIRECTION: str | None = None
    LOCATION: str | None = None
    SETTINGS: dict[str, Any] | None = None
    ORIGIN_ID: str | None = None
    ORIGINATOR_ID: str | None = None
    RESULT_STATUS: int | None = None
    RESULT_STREAM: int | None = None
    RESULT_SOURCE_ID: str | None = None
    PROVIDER_PARAMS: dict[str, Any] | None = None
    PROVIDER_DATA: str | None = None
    RESULT_MARK: int | None = None
    RESULT_VALUE: float | None = None
    RESULT_SUM: float | None = None
    RESULT_CURRENCY_ID: str | None = None
    AUTOCOMPLETE_RULE: int | None = None
    COMMUNICATIONS: list[ActivityCommunication] | None = None
    FILES: list[dict[str, Any]] | None = None
    WEBDAV_ELEMENTS: list[dict[str, Any]] | None = None

    model_config = {"extra": "allow"}


class Activity(BaseModel):
    """Activity entity as returned by crm.activity.get / list."""

    ID: int | None = None
    OWNER_ID: int | None = None
    OWNER_TYPE_ID: int | None = None
    TYPE_ID: str | int | None = None
    PROVIDER_ID: str | None = None
    PROVIDER_TYPE_ID: str | None = None
    PROVIDER_GROUP_ID: str | None = None
    ASSOCIATED_ENTITY_ID: int | None = None
    SUBJECT: str | None = None
    START_TIME: str | None = None
    END_TIME: str | None = None
    DEADLINE: str | None = None
    COMPLETED: str | None = None
    STATUS: str | int | None = None
    RESPONSIBLE_ID: int | None = None
    PRIORITY: str | int | None = None
    NOTIFY_TYPE: str | int | None = None
    NOTIFY_VALUE: int | None = None
    DESCRIPTION: str | None = None
    DESCRIPTION_TYPE: str | int | None = None
    DIRECTION: str | int | None = None
    LOCATION: str | None = None
    CREATED: str | None = None
    AUTHOR_ID: int | None = None
    LAST_UPDATED: str | None = None
    EDITOR_ID: int | None = None
    SETTINGS: dict[str, Any] | None = None
    ORIGIN_ID: str | None = None
    ORIGINATOR_ID: str | None = None
    RESULT_STATUS: int | None = None
    RESULT_STREAM: int | None = None
    RESULT_SOURCE_ID: str | None = None
    PROVIDER_PARAMS: dict[str, Any] | None = None
    PROVIDER_DATA: str | None = None
    RESULT_MARK: int | None = None
    RESULT_VALUE: float | None = None
    RESULT_SUM: float | None = None
    RESULT_CURRENCY_ID: str | None = None
    AUTOCOMPLETE_RULE: int | None = None
    BINDINGS: list[dict[str, Any]] | None = None
    COMMUNICATIONS: list[ActivityCommunication] | None = None
    FILES: list[dict[str, Any]] | None = None
    WEBDAV_ELEMENTS: list[dict[str, Any]] | None = None
    IS_INCOMING_CHANNEL: str | None = None

    model_config = {"extra": "allow", "populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        """Full dict representation including extra fields from API."""
        data = self.model_dump(mode="json")
        extra = getattr(self, "__pydantic_extra__", None)
        if extra:
            data.update(extra)
        return data
