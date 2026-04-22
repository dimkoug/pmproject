"""Inventory barcode + FIFO + bins (Phase 3 #5)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestBarcodeLookup:
    async def test_by_barcode_returns_product(self, client: AsyncClient):
        # Create via POST (router). The barcode field isn't in the legacy
        # ProductCreate schema, so set it directly afterwards.
        prod = (await client.post("/api/erp/products", json={
            "sku": "BC-1", "name": "Scannable", "unit_price": 1.0,
        })).json()
        from tests.conftest import async_session_test
        from app.models.erp import Product
        from uuid import UUID
        async with async_session_test() as db:
            p = await db.get(Product, UUID(prod["id"]))
            p.barcode = "1234567890123"
            await db.commit()

        r = await client.get("/api/erp/products/by-barcode/1234567890123")
        assert r.status_code == 200
        assert r.json()["sku"] == "BC-1"

    async def test_unknown_barcode_is_404(self, client: AsyncClient):
        r = await client.get("/api/erp/products/by-barcode/does-not-exist")
        assert r.status_code == 404


class TestWarehouseBins:
    async def test_create_and_list_bins(self, client: AsyncClient):
        wh = (await client.post("/api/erp/warehouses", json={"code": "W1", "name": "Main"})).json()
        r = await client.post("/api/erp/warehouse-bins", json={
            "warehouse_id": wh["id"], "code": "A-01", "description": "Row A",
        })
        assert r.status_code == 201
        listing = await client.get(f"/api/erp/warehouses/{wh['id']}/bins")
        codes = {b["code"] for b in listing.json()}
        assert "A-01" in codes


class TestFifoIssue:
    async def _make_setup(self, client: AsyncClient):
        prod = (await client.post("/api/erp/products", json={
            "sku": "FIFO-X", "name": "FIFO X", "unit_price": 10.0, "unit_cost": 5.0,
        })).json()
        wh = (await client.post("/api/erp/warehouses", json={"code": "FW", "name": "FIFO WH"})).json()
        # Seed three batches with ascending mfg_date. FIFO should drain oldest first.
        from tests.conftest import async_session_test
        from app.models.erp import StockBatch
        from uuid import UUID
        async with async_session_test() as db:
            for days_ago, code, qty, cost in [(30, "B1", 5, 4.0), (10, "B2", 5, 5.0), (1, "B3", 5, 6.0)]:
                db.add(StockBatch(
                    product_id=UUID(prod["id"]),
                    warehouse_id=UUID(wh["id"]),
                    batch_code=code,
                    mfg_date=datetime.now(timezone.utc) - timedelta(days=days_ago),
                    qty_received=qty, qty_on_hand=qty, cost_per_unit=cost,
                ))
            await db.commit()
        return prod, wh

    async def test_fifo_drains_oldest_batch_first(self, client: AsyncClient):
        prod, wh = await self._make_setup(client)
        r = await client.post("/api/erp/stock/fifo-issue", json={
            "product_id": prod["id"], "warehouse_id": wh["id"], "quantity": 3,
        })
        assert r.status_code == 200
        body = r.json()
        # Should consume 3 units from B1 (the oldest batch), unit_cost 4.0
        assert len(body["consumed"]) == 1
        assert body["consumed"][0]["batch_code"] == "B1"
        assert body["consumed"][0]["qty_taken"] == 3
        assert body["total_cost"] == 12.0

    async def test_fifo_spans_multiple_batches(self, client: AsyncClient):
        prod, wh = await self._make_setup(client)
        r = await client.post("/api/erp/stock/fifo-issue", json={
            "product_id": prod["id"], "warehouse_id": wh["id"], "quantity": 8,
        })
        body = r.json()
        # Should drain all of B1 (5 @ 4.0) and 3 of B2 (3 @ 5.0) = 20 + 15 = 35
        assert len(body["consumed"]) == 2
        assert body["consumed"][0]["batch_code"] == "B1"
        assert body["consumed"][0]["qty_taken"] == 5
        assert body["consumed"][1]["batch_code"] == "B2"
        assert body["consumed"][1]["qty_taken"] == 3
        assert body["total_cost"] == 35.0

    async def test_fifo_insufficient_stock_raises_400(self, client: AsyncClient):
        prod, wh = await self._make_setup(client)
        r = await client.post("/api/erp/stock/fifo-issue", json={
            "product_id": prod["id"], "warehouse_id": wh["id"], "quantity": 100,
        })
        assert r.status_code == 400
        assert "Insufficient" in r.json().get("detail", "")

    async def test_fifo_zero_quantity_rejected(self, client: AsyncClient):
        prod, wh = await self._make_setup(client)
        r = await client.post("/api/erp/stock/fifo-issue", json={
            "product_id": prod["id"], "warehouse_id": wh["id"], "quantity": 0,
        })
        assert r.status_code == 400

    async def test_fifo_decrements_qty_on_hand(self, client: AsyncClient):
        prod, wh = await self._make_setup(client)
        await client.post("/api/erp/stock/fifo-issue", json={
            "product_id": prod["id"], "warehouse_id": wh["id"], "quantity": 7,
        })
        from tests.conftest import async_session_test
        from sqlalchemy import select
        from app.models.erp import StockBatch
        from uuid import UUID
        async with async_session_test() as db:
            rows = (await db.execute(
                select(StockBatch).where(StockBatch.product_id == UUID(prod["id"]))
                .order_by(StockBatch.mfg_date)
            )).scalars().all()
        # B1 fully drained (0), B2 partially drained (3), B3 untouched (5)
        totals = {r.batch_code: r.qty_on_hand for r in rows}
        assert totals["B1"] == 0
        assert totals["B2"] == 3
        assert totals["B3"] == 5
