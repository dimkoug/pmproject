"""Returns / refunds (Phase 3 #3).

Covers:
  * POST /api/returns creates RMA + lines + computes refund_amount
  * GET /api/returns lists returns and can filter by invoice_id
  * PATCH /api/returns/{id}/status transitions and sets timestamps
  * 404 paths
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _make_invoice(client: AsyncClient) -> dict:
    co = (await client.post("/api/crm/companies", json={"name": "Returny"})).json()
    inv = (await client.post("/api/erp/invoices", json={
        "invoice_number": "INV-RMA-001",
        "invoice_type": "receivable",
        "company_id": co["id"],
        "items": [{"description": "Widget", "quantity": 5, "unit_price": 10.0}],
    })).json()
    return inv


class TestCreateReturn:
    async def test_create_return_computes_refund_amount(self, client: AsyncClient):
        inv = await _make_invoice(client)
        r = await client.post("/api/returns", json={
            "invoice_id": inv["id"],
            "rma_number": "RMA-001",
            "reason": "Damaged in transit",
            "lines": [
                {"description": "Widget A", "quantity": 2, "unit_price": 10.0},
                {"description": "Widget B", "quantity": 1, "unit_price": 5.0},
            ],
        })
        assert r.status_code == 201
        assert r.json()["rma_number"] == "RMA-001"

        # Refund amount rollup is 2*10 + 1*5 = 25
        from tests.conftest import async_session_test
        from sqlalchemy import select
        from app.models.pricing import ReturnMerchandise, ReturnLine
        async with async_session_test() as db:
            rma = (await db.execute(
                select(ReturnMerchandise).where(ReturnMerchandise.rma_number == "RMA-001")
            )).scalar_one()
            lines = (await db.execute(
                select(ReturnLine).where(ReturnLine.return_id == rma.id)
            )).scalars().all()
        assert rma.refund_amount == 25.0
        assert rma.status.value == "requested"
        assert len(lines) == 2

    async def test_create_return_unknown_invoice(self, client: AsyncClient):
        r = await client.post("/api/returns", json={
            "invoice_id": "00000000-0000-4000-8000-000000000000",
            "rma_number": "RMA-BAD",
            "lines": [],
        })
        assert r.status_code == 404


class TestListReturns:
    async def test_filter_by_invoice_id(self, client: AsyncClient):
        inv1 = await _make_invoice(client)
        # Second invoice
        co2 = (await client.post("/api/crm/companies", json={"name": "Other"})).json()
        inv2 = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-OTHER", "invoice_type": "receivable",
            "company_id": co2["id"],
            "items": [{"description": "X", "quantity": 1, "unit_price": 1.0}],
        })).json()
        await client.post("/api/returns", json={
            "invoice_id": inv1["id"], "rma_number": "RMA-L1", "lines": [],
        })
        await client.post("/api/returns", json={
            "invoice_id": inv2["id"], "rma_number": "RMA-L2", "lines": [],
        })
        r = await client.get(f"/api/returns?invoice_id={inv1['id']}")
        rmas = {row["rma_number"] for row in r.json()}
        assert "RMA-L1" in rmas
        assert "RMA-L2" not in rmas


class TestReturnStatusTransitions:
    async def test_received_sets_received_at(self, client: AsyncClient):
        inv = await _make_invoice(client)
        rma = (await client.post("/api/returns", json={
            "invoice_id": inv["id"], "rma_number": "RMA-S1",
            "lines": [{"description": "X", "quantity": 1, "unit_price": 1.0}],
        })).json()
        r = await client.patch(f"/api/returns/{rma['id']}/status?new_status=received")
        assert r.status_code == 200
        assert r.json()["status"] == "received"

        from tests.conftest import async_session_test
        from app.models.pricing import ReturnMerchandise
        from uuid import UUID
        async with async_session_test() as db:
            row = await db.get(ReturnMerchandise, UUID(rma["id"]))
        assert row.received_at is not None

    async def test_refunded_sets_refunded_at(self, client: AsyncClient):
        inv = await _make_invoice(client)
        rma = (await client.post("/api/returns", json={
            "invoice_id": inv["id"], "rma_number": "RMA-S2",
            "lines": [{"description": "X", "quantity": 1, "unit_price": 1.0}],
        })).json()
        await client.patch(f"/api/returns/{rma['id']}/status?new_status=refunded")

        from tests.conftest import async_session_test
        from app.models.pricing import ReturnMerchandise
        from uuid import UUID
        async with async_session_test() as db:
            row = await db.get(ReturnMerchandise, UUID(rma["id"]))
        assert row.refunded_at is not None
        assert row.status.value == "refunded"

    async def test_status_update_unknown_id(self, client: AsyncClient):
        r = await client.patch(
            "/api/returns/00000000-0000-4000-8000-000000000000/status?new_status=approved"
        )
        assert r.status_code == 404
