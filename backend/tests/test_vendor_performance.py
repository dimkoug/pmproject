"""Vendor performance (Phase 3 #4).

Covers:
  * POST /api/erp/purchase-orders/{id}/receive stamps received_date + defect_rate
  * defect_rate validation (must be 0..1)
  * GET /api/erp/vendors/{id}/performance aggregates on-time rate, avg days late, defect
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _make_vendor(client: AsyncClient) -> dict:
    r = await client.post("/api/erp/vendors", json={"name": "Acme Supply"})
    return r.json()


async def _make_po(client: AsyncClient, vendor_id: str, delivery_date: datetime | None, total: float = 100.0) -> dict:
    # Use the real router POST for PO
    payload = {
        "vendor_id": vendor_id,
        "po_number": f"PO-{datetime.now(timezone.utc).timestamp():.0f}",
        "total_amount": total,
    }
    r = await client.post("/api/erp/purchase-orders", json=payload)
    po = r.json()
    # Set delivery_date directly on the model since the endpoint doesn't accept it
    if delivery_date is not None:
        from tests.conftest import async_session_test
        from app.models.erp import PurchaseOrder
        from uuid import UUID
        async with async_session_test() as db:
            obj = await db.get(PurchaseOrder, UUID(po["id"]))
            obj.delivery_date = delivery_date
            await db.commit()
    return po


class TestReceivePo:
    async def test_receive_stamps_received_date(self, client: AsyncClient):
        v = await _make_vendor(client)
        po = await _make_po(client, v["id"], None)
        r = await client.post(f"/api/erp/purchase-orders/{po['id']}/receive", json={})
        assert r.status_code == 200
        assert "received_date" in r.json()

    async def test_receive_rejects_defect_rate_out_of_range(self, client: AsyncClient):
        v = await _make_vendor(client)
        po = await _make_po(client, v["id"], None)
        r = await client.post(f"/api/erp/purchase-orders/{po['id']}/receive", json={
            "defect_rate": 1.5,  # > 1.0
        })
        assert r.status_code == 400
        r2 = await client.post(f"/api/erp/purchase-orders/{po['id']}/receive", json={
            "defect_rate": -0.1,
        })
        assert r2.status_code == 400

    async def test_receive_accepts_edge_values(self, client: AsyncClient):
        v = await _make_vendor(client)
        po = await _make_po(client, v["id"], None)
        r0 = await client.post(f"/api/erp/purchase-orders/{po['id']}/receive", json={"defect_rate": 0.0})
        assert r0.status_code == 200
        po2 = await _make_po(client, v["id"], None)
        r1 = await client.post(f"/api/erp/purchase-orders/{po2['id']}/receive", json={"defect_rate": 1.0})
        assert r1.status_code == 200

    async def test_receive_unknown_po(self, client: AsyncClient):
        r = await client.post(
            "/api/erp/purchase-orders/00000000-0000-4000-8000-000000000000/receive",
            json={},
        )
        assert r.status_code == 404


class TestPerformanceAggregate:
    async def test_zero_received_gives_null_on_time_rate(self, client: AsyncClient):
        v = await _make_vendor(client)
        r = await client.get(f"/api/erp/vendors/{v['id']}/performance")
        assert r.status_code == 200
        body = r.json()
        assert body["po_count"] == 0
        assert body["on_time_rate"] is None
        assert body["avg_days_late"] == 0.0

    async def test_on_time_rate_computed(self, client: AsyncClient):
        """Two POs received on time, one received late → on_time_rate = 2/3."""
        v = await _make_vendor(client)
        base = datetime.now(timezone.utc)
        # On-time × 2
        po1 = await _make_po(client, v["id"], base + timedelta(days=5))
        po2 = await _make_po(client, v["id"], base + timedelta(days=5))
        # Late × 1 (received 3 days after delivery_date)
        po3 = await _make_po(client, v["id"], base + timedelta(days=5))

        # Set received_date directly so we control timing deterministically
        from tests.conftest import async_session_test
        from app.models.erp import PurchaseOrder
        from uuid import UUID
        async with async_session_test() as db:
            for pid, received in [
                (po1["id"], base + timedelta(days=3)),       # on time
                (po2["id"], base + timedelta(days=5)),       # exactly on due date = on time
                (po3["id"], base + timedelta(days=8)),       # 3 days late
            ]:
                obj = await db.get(PurchaseOrder, UUID(pid))
                obj.received_date = received
            await db.commit()

        r = await client.get(f"/api/erp/vendors/{v['id']}/performance")
        body = r.json()
        assert body["po_count"] == 3
        assert body["received_count"] == 3
        # 2 of 3 on-time
        assert abs(body["on_time_rate"] - 2/3) < 1e-6
        # The single late shipment was 3 days late
        assert body["avg_days_late"] == 3.0

    async def test_defect_rate_averaged_over_non_null(self, client: AsyncClient):
        v = await _make_vendor(client)
        po1 = await _make_po(client, v["id"], None)
        po2 = await _make_po(client, v["id"], None)
        po3 = await _make_po(client, v["id"], None)
        await client.post(f"/api/erp/purchase-orders/{po1['id']}/receive", json={"defect_rate": 0.1})
        await client.post(f"/api/erp/purchase-orders/{po2['id']}/receive", json={"defect_rate": 0.3})
        await client.post(f"/api/erp/purchase-orders/{po3['id']}/receive", json={})  # null

        r = await client.get(f"/api/erp/vendors/{v['id']}/performance")
        # (0.1 + 0.3) / 2 = 0.2
        assert abs(r.json()["defect_rate"] - 0.2) < 1e-6

    async def test_performance_404_unknown_vendor(self, client: AsyncClient):
        r = await client.get("/api/erp/vendors/00000000-0000-4000-8000-000000000000/performance")
        assert r.status_code == 404
