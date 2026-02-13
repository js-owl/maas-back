"""Unit tests for Bitrix24 client and DealService (mocked responses)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.bitrix24.client import BitrixClient
from backend.bitrix24.exceptions import BitrixAPIError
from backend.bitrix24.dto.deal import DealCreate, DealUpdate
from backend.bitrix24.dto.product import ProductCreate, ProductUpdate
from backend.bitrix24.services.deal import DealService
from backend.bitrix24.services.product import ProductService


@pytest.mark.unit
@pytest.mark.asyncio
class TestBitrixClient:
    """Tests for BitrixClient with mocked HTTP."""

    async def test_call_success_returns_result(self):
        """Client returns result on success response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": 42, "time": {}}
        mock_response.raise_for_status = MagicMock()

        with patch("backend.bitrix24.client.httpx.AsyncClient") as mock_client_cls:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value.post = mock_post
            client = BitrixClient("https://portal.bitrix24.com/rest/1/abc/")
            result = await client.call("crm.deal.get", {"id": 1})
            assert result == 42
            mock_post.assert_called_once()
            call_kw = mock_post.call_args[1]
            assert call_kw["json"] == {"id": 1}
            assert "crm.deal.get" in mock_post.call_args[0][0]

    async def test_call_excludes_none_from_payload(self):
        """Client excludes None values from request payload."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": 1}
        mock_response.raise_for_status = MagicMock()

        with patch("backend.bitrix24.client.httpx.AsyncClient") as mock_client_cls:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value.post = mock_post
            client = BitrixClient("https://portal.bitrix24.com/rest/1/abc/")
            await client.call("crm.deal.add", {"fields": {"TITLE": "Deal"}, "x": None})
            call_kw = mock_post.call_args[1]
            assert call_kw["json"] == {"fields": {"TITLE": "Deal"}}

    async def test_call_error_raises_bitrix_api_error(self):
        """Client raises BitrixAPIError on error response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "QUERY_LIMIT_EXCEEDED",
            "error_description": "Too many requests",
        }

        with patch("backend.bitrix24.client.httpx.AsyncClient") as mock_client_cls:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value.post = mock_post
            client = BitrixClient("https://portal.bitrix24.com/rest/1/abc/")
            with pytest.raises(BitrixAPIError) as exc_info:
                await client.call("crm.deal.get", {"id": 1})
            assert exc_info.value.code == "QUERY_LIMIT_EXCEEDED"
            assert "Too many requests" in exc_info.value.description

    async def test_oauth_adds_auth_to_body(self):
        """When access_token is set, client adds auth to request body."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": 1}

        with patch("backend.bitrix24.client.httpx.AsyncClient") as mock_client_cls:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value.post = mock_post
            client = BitrixClient(
                "https://portal.bitrix24.com/rest/",
                access_token="secret",
            )
            await client.call("crm.deal.get", {"id": 1})
            call_kw = mock_post.call_args[1]
            assert call_kw["json"]["auth"] == "secret"
            assert call_kw["json"]["id"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestDealService:
    """Tests for DealService with mocked BitrixClient."""

    async def test_add_returns_created_id(self):
        """DealService.add calls crm.deal.add and returns deal ID."""
        mock_client = AsyncMock()
        mock_client.call.return_value = 123
        service = DealService(mock_client)
        dto = DealCreate(TITLE="Test Deal", STAGE_ID="NEW")
        result = await service.add(dto)
        assert result == 123
        mock_client.call.assert_called_once_with("crm.deal.add", {"fields": {"TITLE": "Test Deal", "STAGE_ID": "NEW"}})

    async def test_get_returns_deal_dto(self):
        """DealService.get calls crm.deal.get and returns Deal DTO."""
        mock_client = AsyncMock()
        mock_client.call.return_value = {"id": "1", "TITLE": "Deal 1"}
        service = DealService(mock_client)
        result = await service.get(1)
        assert result.ID == "1"
        assert result.TITLE == "Deal 1"
        mock_client.call.assert_called_once_with("crm.deal.get", {"id": 1})

    async def test_list_returns_list_of_deals(self):
        """DealService.list calls crm.deal.list and returns list of Deal DTOs."""
        mock_client = AsyncMock()
        mock_client.call.return_value = [
            {"id": "1", "TITLE": "A"},
            {"id": "2", "TITLE": "B"},
        ]
        service = DealService(mock_client)
        result = await service.list(filter={"STAGE_ID": "NEW"})
        assert len(result) == 2
        assert result[0].ID == "1" and result[0].TITLE == "A"
        assert result[1].ID == "2" and result[1].TITLE == "B"
        mock_client.call.assert_called_once_with("crm.deal.list", {"filter": {"STAGE_ID": "NEW"}})

    async def test_update_calls_crm_deal_update(self):
        """DealService.update calls crm.deal.update."""
        mock_client = AsyncMock()
        service = DealService(mock_client)
        result = await service.update(1, DealUpdate(TITLE="Updated"))
        assert result is True
        mock_client.call.assert_called_once_with("crm.deal.update", {"id": 1, "fields": {"TITLE": "Updated"}})

    async def test_delete_calls_crm_deal_delete(self):
        """DealService.delete calls crm.deal.delete."""
        mock_client = AsyncMock()
        service = DealService(mock_client)
        result = await service.delete(1)
        assert result is True
        mock_client.call.assert_called_once_with("crm.deal.delete", {"id": 1})

    async def test_add_merges_userfields_into_fields(self):
        """DealService.add merges userfields (UF_CRM_*) into the fields payload."""
        mock_client = AsyncMock()
        mock_client.call.return_value = 456
        service = DealService(mock_client)
        dto = DealCreate(TITLE="Deal", userfields={"UF_CRM_123": "custom"})
        result = await service.add(dto)
        assert result == 456
        mock_client.call.assert_called_once()
        call_args = mock_client.call.call_args[0][1]
        assert call_args["fields"]["TITLE"] == "Deal"
        assert call_args["fields"]["UF_CRM_123"] == "custom"
        assert "userfields" not in call_args["fields"]

    async def test_update_merges_userfields_into_fields(self):
        """DealService.update merges userfields into the fields payload."""
        mock_client = AsyncMock()
        service = DealService(mock_client)
        dto = DealUpdate(STAGE_ID="WON", userfields={"UF_CRM_456": "done"})
        result = await service.update(1, dto)
        assert result is True
        call_args = mock_client.call.call_args[0][1]
        assert call_args["fields"]["STAGE_ID"] == "WON"
        assert call_args["fields"]["UF_CRM_456"] == "done"
        assert "userfields" not in call_args["fields"]


@pytest.mark.unit
@pytest.mark.asyncio
class TestProductService:
    """Tests for ProductService with mocked BitrixClient."""

    async def test_add_merges_properties_into_fields(self):
        """ProductService.add merges product properties into the fields payload."""
        mock_client = AsyncMock()
        mock_client.call.return_value = 789
        service = ProductService(mock_client)
        dto = ProductCreate(name="Widget", properties={"PROPERTY_1": "value"})
        result = await service.add(dto)
        assert result == 789
        mock_client.call.assert_called_once()
        call_args = mock_client.call.call_args[0][1]
        assert call_args["fields"]["name"] == "Widget"
        assert call_args["fields"]["PROPERTY_1"] == "value"
        assert "properties" not in call_args["fields"]

    async def test_update_merges_properties_into_fields(self):
        """ProductService.update merges product properties into the fields payload."""
        mock_client = AsyncMock()
        service = ProductService(mock_client)
        dto = ProductUpdate(name="Updated", properties={"PROPERTY_2": 42})
        result = await service.update(1, dto)
        assert result is True
        call_args = mock_client.call.call_args[0][1]
        assert call_args["fields"]["name"] == "Updated"
        assert call_args["fields"]["PROPERTY_2"] == 42
        assert "properties" not in call_args["fields"]
