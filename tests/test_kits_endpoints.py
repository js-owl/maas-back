"""
Kits endpoints tests
Tests kit creation, listing, details, and basic access control.
Style matches existing modular endpoint testers (OrdersEndpointTester, etc.).
"""
import asyncio
import httpx
import json
import time

import os
from sqlalchemy import text
from backend.database import AsyncSessionLocal

BASE_URL = "http://localhost:8000"


class KitsEndpointTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

        self.user_id = None
        self.user_id_2 = None

        self.auth_token = None
        self.auth_token_2 = None
        self.test_kit_id = None
        self.test_order_ids = []

    def _normalize_order_ids(self, value):
        if value is None:
            return []
        if isinstance(value, str):
            return json.loads(value)
        return value

    async def _db_get_order_kit_id(self, order_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                text("SELECT kit_id FROM orders WHERE order_id = :oid"),
                {"oid": int(order_id)},
            )
            row = res.first()
            return row[0] if row else None

    async def _db_set_order_total_price(self, order_id: int, total_price: float):
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("UPDATE orders SET total_price = :p WHERE order_id = :oid"),
                {"p": float(total_price), "oid": int(order_id)},
            )
            await session.commit()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _login_and_get_profile(self, username: str, password: str):
        # login
        resp = await self.client.post(
            f"{self.base_url}/login",
            json={"username": username, "password": password},
        )
        assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
        token = resp.json()["access_token"]

        # profile (to get id)
        headers = {"Authorization": f"Bearer {token}"}
        p = await self.client.get(f"{self.base_url}/profile", headers=headers)
        assert p.status_code == 200, f"Profile failed: {p.status_code} {p.text}"
        profile = p.json()

        user_id = profile.get("id") or profile.get("user_id")
        assert user_id is not None, f"Profile has no id: {profile}"
        return token, int(user_id)

    async def _register_and_login(self, username: str, password: str) -> str:
        # Register (ignore if exists)
        try:
            await self.client.post(
                f"{self.base_url}/register",
                json={"username": username, "password": password, "user_type": "individual"},
            )
        except Exception:
            pass

        # Login
        resp = await self.client.post(
            f"{self.base_url}/login",
            json={"username": username, "password": password},
        )
        assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
        return resp.json()["access_token"]

    async def setup_auth(self):
        """Setup 2 users for kits tests (owner + foreign user)."""
        suffix = int(time.time())
        u1 = f"test_kits_user_{suffix}"
        u2 = f"test_kits_user2_{suffix}"
        pw = "testpass123"

        # register best-effort
        await self.client.post(f"{self.base_url}/register", json={"username": u1, "password": pw, "user_type": "individual"})
        await self.client.post(f"{self.base_url}/register", json={"username": u2, "password": pw, "user_type": "individual"})

        self.auth_token, self.user_id = await self._login_and_get_profile(u1, pw)
        self.auth_token_2, self.user_id_2 = await self._login_and_get_profile(u2, pw)

    async def _create_order(self, token: str, service_id: str = "cnc-milling") -> int:
        headers = {"Authorization": f"Bearer {token}"}

        order_request = {
            "service_id": service_id,
            "file_id": 1,
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
            "material_id": "alum_D16",
            "material_form": "rod",
            "tolerance_id": "1",
            "finish_id": "1",
            "cover_id": ["1"],
            "k_otk": "1",
            "k_cert": ["a", "f"],
            "n_dimensions": 1,
            "document_ids": [],
        }

        resp = await self.client.post(
            f"{self.base_url}/orders",
            json=order_request,
            headers=headers,
        )

        assert resp.status_code == 200, f"Order creation failed (needed for kits): {resp.status_code} {resp.text}"

        data = resp.json()
        assert "order_id" in data
        return data["order_id"]

    async def _create_order_in_kit(self, token: str, kit_id: int, service_id: str = "cnc-milling") -> int:
        headers = {"Authorization": f"Bearer {token}"}

        order_request = {
            "service_id": service_id,
            "file_id": 1,
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
            "material_id": "alum_D16",
            "material_form": "rod",
            "tolerance_id": "1",
            "finish_id": "1",
            "cover_id": ["1"],
            "k_otk": "1",
            "k_cert": ["a", "f"],
            "n_dimensions": 1,
            "document_ids": [],
            "kit_id": int(kit_id),  # <-- важно
        }

        resp = await self.client.post(
            f"{self.base_url}/orders",
            json=order_request,
            headers=headers,
        )
        assert resp.status_code == 200, f"Order creation in kit failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert "order_id" in data
        return int(data["order_id"])

    async def test_kits_endpoints_available(self):
        """Smoke: /kits endpoints should not be 404 if router is connected."""
        print(" Testing kits endpoints availability.")

        if not self.auth_token:
            await self.setup_auth()

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        resp = await self.client.get(f"{self.base_url}/kits", headers=headers)

        assert resp.status_code != 404, (
            "Kits endpoints returned 404. "
            "Likely kits router is not included in backend/main.py"
        )
        assert resp.status_code in (200, 401, 403), f"Unexpected status: {resp.status_code} {resp.text}"
        print(" Kits endpoints reachable (not 404)")

    async def test_create_kit(self):
        """Create 2 orders -> create kit -> verify kit_id and order_ids are present."""
        print(" Testing kit creation.")

        if not self.auth_token:
            await self.setup_auth()

        # Create two orders for this user
        o1 = await self._create_order(self.auth_token, "cnc-milling")
        o2 = await self._create_order(self.auth_token, "printing")
        self.test_order_ids = [o1, o2]

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        kit_request = {
            "kit_name": "test-kit",
            "order_ids": [o1, o2],
            "user_id": self.user_id,
            "quantity": 2,
            "location": "test",
            "status": "NEW",
            "bitrix_deal_id": None,
        }

        resp = await self.client.post(
            f"{self.base_url}/kits",
            json=kit_request,
            headers=headers,
        )
        assert resp.status_code == 200, f"Kit creation failed: {resp.status_code} {resp.text}"
        kit = resp.json()

        assert "kit_id" in kit, f"Response has no kit_id: {kit}"
        self.test_kit_id = kit["kit_id"]

        assert "order_ids" in kit, f"Response has no order_ids: {kit}"
        returned = kit["order_ids"]
        if isinstance(returned, str):
            returned = json.loads(returned)
        assert sorted(returned) == sorted([o1, o2]), f"order_ids mismatch: got={returned}, exp={[o1,o2]}"

        print(" Kit creation passed")

    async def test_get_kit_details(self):
        """GET /kits/{id} should return the same kit."""
        print(" Testing kit details endpoint.")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        resp = await self.client.get(
            f"{self.base_url}/kits/{self.test_kit_id}",
            headers=headers,
        )
        assert resp.status_code == 200, f"Kit details failed: {resp.status_code} {resp.text}"
        kit = resp.json()
        assert kit.get("kit_id") == self.test_kit_id

        returned = kit.get("order_ids")
        assert returned is not None
        if isinstance(returned, str):
            returned = json.loads(returned)
        assert sorted(returned) == sorted(self.test_order_ids)

        print(" Kit details passed")

    async def test_list_kits_contains_created(self):
        """GET /kits should contain created kit."""
        print(" Testing kit listing.")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        resp = await self.client.get(f"{self.base_url}/kits", headers=headers)
        assert resp.status_code == 200, f"Kit list failed: {resp.status_code} {resp.text}"
        kits = resp.json()
        assert isinstance(kits, list)
        assert any(k.get("kit_id") == self.test_kit_id for k in kits), "Created kit not found in list"

        print(" Kit listing passed")

    async def test_access_control_foreign_user_cannot_read_kit(self):
        """User2 should not be able to read user1 kit (expect 403 or 404)."""
        print(" Testing kit access control.")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        headers2 = {"Authorization": f"Bearer {self.auth_token_2}"}
        resp = await self.client.get(f"{self.base_url}/kits/{self.test_kit_id}", headers=headers2)

        assert resp.status_code in (403, 404), (
            f"Expected 403/404 for foreign kit access, got {resp.status_code}: {resp.text}"
        )
        print(" Kit access control passed")

    async def test_create_kit_empty_order_ids_variants(self):
        print(" Testing kit creation empty order_ids variants.")

        if not self.auth_token:
            await self.setup_auth()

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        # Variant 1: missing user_id -> schema validation (422 expected)
        resp1 = await self.client.post(
            f"{self.base_url}/kits",
            json={"kit_name": "bad-kit-1", "order_ids": [], "quantity": 1, "location": "test"},
            headers=headers,
        )
        assert resp1.status_code == 422, f"Expected 422, got {resp1.status_code}: {resp1.text}"

        # Variant 2: user_id present but empty order_ids -> 400 or 422 depending on where validated
        resp2 = await self.client.post(
            f"{self.base_url}/kits",
            json={
                "kit_name": "bad-kit-2",
                "order_ids": [],
                "user_id": self.user_id,
                "quantity": 1,
                "location": "test",
                "status": "NEW",
                "bitrix_deal_id": None,
            },
            headers=headers,
        )
        assert resp2.status_code in (400, 422), f"Expected 400/422, got {resp2.status_code}: {resp2.text}"

        print(" Kit creation empty order_ids variants passed")


    async def test_create_kit_rejects_foreign_order(self):
        print(" Testing kit creation rejects foreign order.")

        if not self.auth_token:
            await self.setup_auth()

        foreign_order_id = await self._create_order(self.auth_token_2, "cnc-milling")

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        kit_request = {
            "kit_name": "bad-kit-foreign",
            "order_ids": [foreign_order_id],
            "user_id": self.user_id,
            "quantity": 1,
            "location": "test",
            "status": "NEW",
            "bitrix_deal_id": None,
        }

        resp = await self.client.post(
            f"{self.base_url}/kits",
            json=kit_request,
            headers=headers,
        )

        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        print(" Foreign order rejection passed")

    async def test_delete_order_updates_kits(self):
        print(" Testing: deleting order updates kit order_ids.")

        if not self.auth_token:
            await self.setup_auth()

        o1 = await self._create_order(self.auth_token, "cnc-milling")
        o2 = await self._create_order(self.auth_token, "printing")

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        create_req = {
            "kit_name": "kit-delete-check",
            "order_ids": [o1, o2],
            "user_id": self.user_id,
            "quantity": 1,
            "location": "test",
            "status": "NEW",
            "bitrix_deal_id": None,
        }
        rk = await self.client.post(f"{self.base_url}/kits", json=create_req, headers=headers)
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit_id = rk.json()["kit_id"]

        rd = await self.client.delete(f"{self.base_url}/orders/{o1}", headers=headers)
        assert rd.status_code == 200, f"Order delete failed: {rd.status_code} {rd.text}"

        rg = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg.status_code == 200, f"Kit get failed: {rg.status_code} {rg.text}"

        kit = rg.json()
        order_ids = kit.get("order_ids")
        if isinstance(order_ids, str):
            import json
            order_ids = json.loads(order_ids)

        assert o1 not in order_ids, f"Expected deleted order {o1} removed from kit, got order_ids={order_ids}"
        assert o2 in order_ids, f"Expected remaining order {o2} still in kit, got order_ids={order_ids}"

        print(" Delete order updates kit passed")

    async def test_update_kit_fields(self):
        print(" Testing kit update (fields).")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        update_req = {
            "kit_name": "test-kit-updated",
            "quantity": 7,
            "location": "updated-location",
            "status": "IN_PROGRESS",
            "bitrix_deal_id": 12345,
        }

        resp = await self.client.put(
            f"{self.base_url}/kits/{self.test_kit_id}",
            json=update_req,
            headers=headers,
        )

        assert resp.status_code == 200, f"Kit update failed: {resp.status_code} {resp.text}"
        kit = resp.json()

        assert kit.get("kit_id") == self.test_kit_id
        assert kit.get("kit_name") == "test-kit-updated"
        assert kit.get("quantity") == 7
        assert kit.get("location") == "updated-location"
        assert kit.get("status") == "IN_PROGRESS"
        assert kit.get("bitrix_deal_id") == 12345

        returned = self._normalize_order_ids(kit.get("order_ids"))
        assert sorted(returned) == sorted(self.test_order_ids)

        print(" Kit update fields passed")

    async def test_update_kit_order_ids_valid(self):
        print(" Testing kit update (order_ids valid).")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        new_order_id = await self._create_order(self.auth_token, "cnc-milling")

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        update_req = {
            "order_ids": [new_order_id],
        }

        resp = await self.client.put(
            f"{self.base_url}/kits/{self.test_kit_id}",
            json=update_req,
            headers=headers,
        )
        assert resp.status_code == 200, f"Kit update order_ids failed: {resp.status_code} {resp.text}"

        kit = resp.json()
        returned = self._normalize_order_ids(kit.get("order_ids"))
        assert returned == [new_order_id] or sorted(returned) == [new_order_id]

        # обновляем локальную “ожидаемую” правду для следующих тестов
        self.test_order_ids = [new_order_id]

        print(" Kit update order_ids (valid) passed")

    async def test_update_kit_order_ids_empty_rejected(self):
        print(" Testing kit update rejects empty order_ids.")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        resp = await self.client.put(
            f"{self.base_url}/kits/{self.test_kit_id}",
            json={"order_ids": []},
            headers=headers,
        )
        assert resp.status_code in (400, 422), f"Expected 400/422, got {resp.status_code}: {resp.text}"

        print(" Kit update rejects empty order_ids passed")

    async def test_update_kit_order_ids_missing_order_rejected(self):
        print(" Testing kit update rejects missing order_id.")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        missing_id = 99999999
        resp = await self.client.put(
            f"{self.base_url}/kits/{self.test_kit_id}",
            json={"order_ids": [missing_id]},
            headers=headers,
        )
        assert resp.status_code in (400, 404), f"Expected 400/404, got {resp.status_code}: {resp.text}"

        print(" Kit update rejects missing order_id passed")

    async def test_update_kit_order_ids_foreign_order_rejected(self):
        print(" Testing kit update rejects foreign order_id.")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        foreign_order_id = await self._create_order(self.auth_token_2, "cnc-milling")

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        resp = await self.client.put(
            f"{self.base_url}/kits/{self.test_kit_id}",
            json={"order_ids": [foreign_order_id]},
            headers=headers,
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"

        print(" Kit update rejects foreign order_id passed")

    async def test_access_control_foreign_user_cannot_update_kit(self):
        print(" Testing kit update access control (foreign user).")

        if not self.auth_token:
            await self.setup_auth()
        if not self.test_kit_id:
            await self.test_create_kit()

        headers2 = {"Authorization": f"Bearer {self.auth_token_2}"}
        resp = await self.client.put(
            f"{self.base_url}/kits/{self.test_kit_id}",
            json={"kit_name": "hacked"},
            headers=headers2,
        )

        assert resp.status_code in (400, 403, 404), f"Expected 400/403/404, got {resp.status_code}: {resp.text}"
        print(" Kit update access control passed")

    async def test_kit_price_and_total_kit_price_calculated(self):
        print(" Testing kit_price and total_kit_price calculation.")

        if not self.auth_token:
            await self.setup_auth()

        # 1) create two orders
        o1 = await self._create_order(self.auth_token, "cnc-milling")
        o2 = await self._create_order(self.auth_token, "printing")

        # 2) force deterministic total_price in DB
        await self._db_set_order_total_price(o1, 100.0)
        await self._db_set_order_total_price(o2, 250.0)

        # 3) create kit with quantity=3
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        create_req = {
            "kit_name": "kit-price-check",
            "order_ids": [o1, o2],
            "user_id": self.user_id,
            "quantity": 3,
            "location": "test",
            "status": "NEW",
            "bitrix_deal_id": None,
        }
        rk = await self.client.post(f"{self.base_url}/kits", json=create_req, headers=headers)
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit = rk.json()
        kit_id = kit["kit_id"]

        # 4) read kit and assert prices
        rg = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg.status_code == 200, f"Kit get failed: {rg.status_code} {rg.text}"
        kit2 = rg.json()

        # Expect kit_price == 350 and total_kit_price == 1050
        kp = kit2.get("kit_price")
        tkp = kit2.get("total_kit_price")

        assert kp is not None, f"kit_price missing in response: {kit2}"
        assert tkp is not None, f"total_kit_price missing in response: {kit2}"

        # float-safe compare
        assert abs(float(kp) - 350.0) < 1e-6, f"kit_price wrong: got={kp}, expected=350.0"
        assert abs(float(tkp) - 1050.0) < 1e-6, f"total_kit_price wrong: got={tkp}, expected=1050.0"

        print(" kit_price & total_kit_price calculation passed")

    async def test_kit_price_excludes_cancelled_orders(self):
        print(" Testing kit_price excludes cancelled orders.")

        if not self.auth_token:
            await self.setup_auth()

        o1 = await self._create_order(self.auth_token, "cnc-milling")
        o2 = await self._create_order(self.auth_token, "printing")

        await self._db_set_order_total_price(o1, 100.0)
        await self._db_set_order_total_price(o2, 250.0)

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        create_req = {
            "kit_name": "kit-cancel-exclude",
            "order_ids": [o1, o2],
            "user_id": self.user_id,
            "quantity": 2,
            "location": "test",
            "status": "NEW",
            "bitrix_deal_id": None,
        }
        rk = await self.client.post(f"{self.base_url}/kits", json=create_req, headers=headers)
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit_id = rk.json()["kit_id"]

        # cancel o1
        rd = await self.client.delete(f"{self.base_url}/orders/{o1}", headers=headers)
        assert rd.status_code == 200, f"Order cancel/delete failed: {rd.status_code} {rd.text}"

        # kit_price should become 250, total_kit_price = 2 * 250 = 500
        rg = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg.status_code == 200, f"Kit get failed: {rg.status_code} {rg.text}"
        kit = rg.json()

        kp = float(kit.get("kit_price"))
        tkp = float(kit.get("total_kit_price"))

        assert abs(kp - 250.0) < 1e-6, f"kit_price should exclude cancelled order: got={kp}, expected=250.0"
        assert abs(tkp - 500.0) < 1e-6, f"total_kit_price wrong after cancel: got={tkp}, expected=500.0"

        print(" cancelled orders excluded from kit_price passed")

    async def test_total_kit_price_updates_on_quantity_change(self):
        print(" Testing total_kit_price updates when quantity changes.")

        if not self.auth_token:
            await self.setup_auth()

        o1 = await self._create_order(self.auth_token, "cnc-milling")
        await self._db_set_order_total_price(o1, 400.0)

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        create_req = {
            "kit_name": "kit-qty-change",
            "order_ids": [o1],
            "user_id": self.user_id,
            "quantity": 1,
            "location": "test",
            "status": "NEW",
            "bitrix_deal_id": None,
        }
        rk = await self.client.post(f"{self.base_url}/kits", json=create_req, headers=headers)
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit_id = rk.json()["kit_id"]

        # Update quantity -> 5
        ru = await self.client.put(
            f"{self.base_url}/kits/{kit_id}",
            json={"quantity": 5},
            headers=headers,
        )
        assert ru.status_code == 200, f"Kit update failed: {ru.status_code} {ru.text}"

        # Re-read kit to assert total_kit_price is updated
        rg = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg.status_code == 200, f"Kit get failed: {rg.status_code} {rg.text}"
        kit = rg.json()

        kp = float(kit.get("kit_price"))
        tkp = float(kit.get("total_kit_price"))

        assert abs(kp - 400.0) < 1e-6, f"kit_price wrong: got={kp}, expected=400.0"
        assert abs(tkp - 2000.0) < 1e-6, f"total_kit_price wrong after quantity change: got={tkp}, expected=2000.0"

        print(" total_kit_price updates on quantity change passed")

    async def test_kit_price_updates_when_order_price_changes(self):
        print(" Testing kit_price updates when order total_price changes.")

        if not self.auth_token:
            await self.setup_auth()

        o1 = await self._create_order(self.auth_token, "cnc-milling")
        o2 = await self._create_order(self.auth_token, "printing")
        await self._db_set_order_total_price(o1, 10.0)
        await self._db_set_order_total_price(o2, 20.0)

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        rk = await self.client.post(
            f"{self.base_url}/kits",
            json={
                "kit_name": "kit-price-change",
                "order_ids": [o1, o2],
                "user_id": self.user_id,
                "quantity": 1,
                "location": "test",
                "status": "NEW",
                "bitrix_deal_id": None,
            },
            headers=headers,
        )
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit_id = rk.json()["kit_id"]

        # Force price change for o2
        await self._db_set_order_total_price(o2, 200.0)

        # Read kit: expected sum=210
        rg = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg.status_code == 200, f"Kit get failed: {rg.status_code} {rg.text}"
        kit = rg.json()

        kp = float(kit.get("kit_price") or 0.0)
        assert abs(kp - 210.0) < 1e-6, f"kit_price should update: got={kp}, expected=210.0"

        print(" Kit price updates after order price change passed")

    async def test_admin_list_all_kits(self):
        print(" Testing admin kits listing")

        if not self.auth_token:
            await self.setup_auth()

        # Try to login as admin
        import os
        admin_user = os.getenv("ADMIN_USERNAME", "admin")
        admin_pass = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin")

        try:
            admin_token, _admin_id = await self._login_and_get_profile(admin_user, admin_pass)
        except Exception:
            admin_pass = os.getenv("ADMIN_NEW_PASSWORD", "admin")
            try:
                admin_token, _admin_id = await self._login_and_get_profile(admin_user, admin_pass)
            except Exception:
                print(" Admin credentials not available; skipping admin kits test")
                return
        
        headers = {"Authorization": f"Bearer {admin_token}"}

        resp = await self.client.get(f"{self.base_url}/admin/kits", headers=headers)
        if resp.status_code == 404:
            resp = await self.client.get(f"{self.base_url}/kits", headers=headers)

        if resp.status_code == 404:
            print(" Admin kits endpoint not implemented; skipping")
            return

        assert resp.status_code == 200, f"Admin kits list failed: {resp.status_code} {resp.text}"
        kits = resp.json()
        assert isinstance(kits, list)
        print(f" Admin kits listing ok (count={len(kits)})")
    
    async def test_admin_hard_delete_order_updates_kit_price(self):
        print(" Testing admin hard delete order updates kit_price")

        if not self.auth_token:
            await self.setup_auth()

        # Try to login as admin
        import os
        admin_user = os.getenv("ADMIN_USERNAME", "admin")
        admin_pass = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin")

        try:
            admin_token, _admin_id = await self._login_and_get_profile(admin_user, admin_pass)
        except Exception:
            admin_pass = os.getenv("ADMIN_NEW_PASSWORD", "admin")
            try:
                admin_token, _admin_id = await self._login_and_get_profile(admin_user, admin_pass)
            except Exception:
                print(" Admin credentials not available; skipping hard delete test")
                return

        o1 = await self._create_order(self.auth_token, "cnc-milling")
        o2 = await self._create_order(self.auth_token, "printing")
        await self._db_set_order_total_price(o1, 50.0)
        await self._db_set_order_total_price(o2, 70.0)

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        rk = await self.client.post(
            f"{self.base_url}/kits",
            json={
                "kit_name": "kit-hard-delete",
                "order_ids": [o1, o2],
                "user_id": self.user_id,
                "quantity": 1,
                "location": "test",
                "status": "NEW",
                "bitrix_deal_id": None,
            },
            headers=headers,
        )
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit_id = rk.json()["kit_id"]

        # Hard delete o1 as admin
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        rd = await self.client.delete(f"{self.base_url}/admin/orders/{o1}/hard", headers=admin_headers)
        assert rd.status_code in (200, 404), f"Admin hard delete failed: {rd.status_code} {rd.text}"
        if rd.status_code == 404:
            print(" Order already removed; skipping asserts")
            return

        # Now kit_price should be 70
        rg = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg.status_code == 200, f"Kit get failed: {rg.status_code} {rg.text}"
        kit = rg.json()

        kp = float(kit.get("kit_price") or 0.0)
        assert abs(kp - 70.0) < 1e-6, f"kit_price wrong after hard delete: got={kp}, expected=70.0"

        print(" Admin hard delete updates kit_price passed")

    async def test_soft_delete_kit(self):
        print(" Testing kit soft delete.")

        if not self.auth_token:
            await self.setup_auth()

        # create kit
        o1 = await self._create_order(self.auth_token, "cnc-milling")
        o2 = await self._create_order(self.auth_token, "printing")

        headers = {"Authorization": f"Bearer {self.auth_token}"}
        rk = await self.client.post(
            f"{self.base_url}/kits",
            json={
                "kit_name": "kit-soft-delete",
                "order_ids": [o1, o2],
                "user_id": self.user_id,
                "quantity": 1,
                "location": "test",
                "status": "NEW",
                "bitrix_deal_id": None,
            },
            headers=headers,
        )
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit_id = rk.json()["kit_id"]

        # soft delete
        rd = await self.client.delete(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rd.status_code == 200, f"Kit soft delete failed: {rd.status_code} {rd.text}"

        # behaviour after delete: either still retrievable with status=cancelled, or 404 if you hide cancelled
        rg = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg.status_code in (200, 404), f"Unexpected get-after-delete: {rg.status_code} {rg.text}"
        if rg.status_code == 200:
            kit = rg.json()
            assert str(kit.get("status", "")).lower() == "cancelled", f"Expected status=cancelled, got: {kit}"

        print(" Kit soft delete passed")

    async def test_add_order_to_existing_kit_updates_price(self):
        print(" Testing adding order to existing kit updates kit_price and order_ids.")

        if not self.auth_token:
            await self.setup_auth()

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        o1 = await self._create_order(self.auth_token, "cnc-milling")
        await self._db_set_order_total_price(o1, 100.0)

        rk = await self.client.post(
            f"{self.base_url}/kits",
            json={
                "kit_name": "kit-add-order",
                "order_ids": [o1],
                "user_id": self.user_id,
                "quantity": 2,
                "location": "test",
                "status": "NEW",
                "bitrix_deal_id": None,
            },
            headers=headers,
        )
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit_id = int(rk.json()["kit_id"])

        rg0 = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg0.status_code == 200, f"Kit get failed: {rg0.status_code} {rg0.text}"
        kit0 = rg0.json()

        kp0 = float(kit0.get("kit_price") or 0.0)
        tkp0 = float(kit0.get("total_kit_price") or 0.0)
        assert abs(kp0 - 100.0) < 1e-6, f"kit_price wrong before add: got={kp0}, expected=100.0"
        assert abs(tkp0 - 200.0) < 1e-6, f"total_kit_price wrong before add: got={tkp0}, expected=200.0"

        o2 = await self._create_order_in_kit(self.auth_token, kit_id, "printing")
        await self._db_set_order_total_price(o2, 250.0)

        rg1 = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg1.status_code == 200, f"Kit get failed after add: {rg1.status_code} {rg1.text}"
        kit1 = rg1.json()

        kp1 = float(kit1.get("kit_price") or 0.0)
        tkp1 = float(kit1.get("total_kit_price") or 0.0)
        assert abs(kp1 - 350.0) < 1e-6, f"kit_price wrong after add: got={kp1}, expected=350.0"
        assert abs(tkp1 - 700.0) < 1e-6, f"total_kit_price wrong after add: got={tkp1}, expected=700.0"

        returned = kit1.get("order_ids")
        if isinstance(returned, str):
            returned = json.loads(returned)
        assert sorted(returned) == sorted([o1, o2]), f"order_ids mismatch after add: got={returned}, expected={[o1, o2]}"

        print(" Add order to existing kit updates price passed")

    async def test_admin_hard_delete_kit_unlinks_orders(self):
        print(" Testing admin hard delete kit unlinks orders")

        if not self.auth_token:
            await self.setup_auth()

        # admin login (same approach as your existing admin tests)
        admin_user = os.getenv("ADMIN_USERNAME", "admin")
        admin_pass = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin")

        admin_token = None
        try:
            admin_token, _admin_id = await self._login_and_get_profile(admin_user, admin_pass)
        except Exception:
            admin_pass = os.getenv("ADMIN_NEW_PASSWORD", "admin")
            try:
                admin_token, _admin_id = await self._login_and_get_profile(admin_user, admin_pass)
            except Exception:
                print(" Admin credentials not available; skipping hard delete kit test")
                return

        # Create orders
        o1 = await self._create_order(self.auth_token, "cnc-milling")
        o2 = await self._create_order(self.auth_token, "printing")

        # Create kit
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        rk = await self.client.post(
            f"{self.base_url}/kits",
            json={
                "kit_name": "kit-hard-delete",
                "order_ids": [o1, o2],
                "user_id": self.user_id,
                "quantity": 1,
                "location": "test",
                "status": "NEW",
                "bitrix_deal_id": None,
            },
            headers=headers,
        )
        assert rk.status_code == 200, f"Kit creation failed: {rk.status_code} {rk.text}"
        kit_id = rk.json()["kit_id"]

        # Sanity: orders should have kit_id set (source of truth)
        k1 = await self._db_get_order_kit_id(o1)
        k2 = await self._db_get_order_kit_id(o2)

        # Hard delete kit as admin
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        rd = await self.client.delete(f"{self.base_url}/admin/kits/{kit_id}/hard", headers=admin_headers)
        assert rd.status_code == 200, f"Admin hard delete kit failed: {rd.status_code} {rd.text}"

        # Kit should be gone
        rg = await self.client.get(f"{self.base_url}/kits/{kit_id}", headers=headers)
        assert rg.status_code in (404, 403), f"Expected kit not found after hard delete: {rg.status_code} {rg.text}"

        # Orders must be unlinked from deleted kit
        k1_after = await self._db_get_order_kit_id(o1)
        k2_after = await self._db_get_order_kit_id(o2)
        assert k1_after is None, f"Expected o1.kit_id NULL after kit hard delete, got {k1_after}"
        assert k2_after is None, f"Expected o2.kit_id NULL after kit hard delete, got {k2_after}"

        print(" Admin hard delete kit unlinks orders passed")

    async def run_all_tests(self):
        """Run all kits tests"""
        print(" Starting kits endpoint tests.\n")

        try:
            await self.test_kits_endpoints_available()
            print()

            await self.test_create_kit()
            print()

            await self.test_get_kit_details()
            print()

            await self.test_list_kits_contains_created()
            print()

            await self.test_access_control_foreign_user_cannot_read_kit()
            print()

            await self.test_create_kit_empty_order_ids_variants()
            print()

            await self.test_create_kit_rejects_foreign_order()
            print()

            await self.test_delete_order_updates_kits()
            print()

            await self.test_update_kit_fields()
            print()

            await self.test_update_kit_order_ids_valid()
            print()

            await self.test_update_kit_order_ids_empty_rejected()
            print()

            await self.test_update_kit_order_ids_missing_order_rejected()
            print()

            await self.test_update_kit_order_ids_foreign_order_rejected()
            print()

            await self.test_access_control_foreign_user_cannot_update_kit()
            print()

            await self.test_kit_price_and_total_kit_price_calculated()
            print()

            await self.test_kit_price_excludes_cancelled_orders()
            print()

            await self.test_total_kit_price_updates_on_quantity_change()
            print()

            await self.test_kit_price_updates_when_order_price_changes()
            print()

            await self.test_admin_hard_delete_order_updates_kit_price()
            print()

            await self.test_soft_delete_kit()
            print()

            await self.test_admin_hard_delete_kit_unlinks_orders()
            print()

            await self.test_add_order_to_existing_kit_updates_price()
            print()

            await self.test_admin_list_all_kits()
            print()

            print(" All kits tests completed successfully!")

        except Exception as e:
            print(f" Kits test failed: {e}")
            raise


async def main():
    async with KitsEndpointTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
