import pytest
from httpx import AsyncClient


class TestAccounts:
    async def test_create_account(self, client: AsyncClient):
        r = await client.post("/api/erp/accounts", json={"code": "1000", "name": "Cash", "account_type": "asset"})
        assert r.status_code == 201
        assert r.json()["code"] == "1000"

    async def test_list_accounts(self, client: AsyncClient):
        await client.post("/api/erp/accounts", json={"code": "2000", "name": "Payables", "account_type": "liability"})
        r = await client.get("/api/erp/accounts")
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestVendors:
    async def test_create_vendor(self, client: AsyncClient):
        r = await client.post("/api/erp/vendors", json={"name": "Acme Corp", "email": "acme@test.com"})
        assert r.status_code == 201
        assert r.json()["name"] == "Acme Corp"

    async def test_list_vendors(self, client: AsyncClient):
        await client.post("/api/erp/vendors", json={"name": "Vendor A"})
        r = await client.get("/api/erp/vendors")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_delete_vendor(self, client: AsyncClient):
        v = (await client.post("/api/erp/vendors", json={"name": "Delete Me"})).json()
        r = await client.delete(f"/api/erp/vendors/{v['id']}")
        assert r.status_code == 204


class TestInvoices:
    async def test_create_invoice(self, client: AsyncClient):
        r = await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-001", "subtotal": 1000, "tax_rate": 10,
        })
        assert r.status_code == 201
        assert r.json()["total"] == 1100.0

    async def test_list_invoices(self, client: AsyncClient):
        await client.post("/api/erp/invoices", json={"invoice_number": "INV-002", "subtotal": 500, "tax_rate": 0})
        r = await client.get("/api/erp/invoices")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_update_invoice_status(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={"invoice_number": "INV-003", "subtotal": 100, "tax_rate": 0})).json()
        r = await client.patch(f"/api/erp/invoices/{inv['id']}?status=paid")
        assert r.status_code == 200
        assert r.json()["status"] == "paid"


class TestExpenses:
    async def test_create_expense(self, client: AsyncClient):
        r = await client.post("/api/erp/expenses", json={"description": "Office supplies", "amount": 150, "category": "materials"})
        assert r.status_code == 201

    async def test_approve_expense(self, client: AsyncClient):
        e = (await client.post("/api/erp/expenses", json={"description": "Travel", "amount": 500})).json()
        r = await client.patch(f"/api/erp/expenses/{e['id']}/approve")
        assert r.status_code == 200
        assert r.json()["is_approved"] is True


class TestPurchaseOrders:
    async def test_create_po(self, client: AsyncClient):
        v = (await client.post("/api/erp/vendors", json={"name": "PO Vendor"})).json()
        r = await client.post("/api/erp/purchase-orders", json={"vendor_id": v["id"], "po_number": "PO-001", "total_amount": 5000})
        assert r.status_code == 201
        assert r.json()["po_number"] == "PO-001"


class TestAssets:
    async def test_create_asset(self, client: AsyncClient):
        r = await client.post("/api/erp/assets", json={"name": "Laptop", "purchase_cost": 1200, "category": "equipment"})
        assert r.status_code == 201

    async def test_list_assets(self, client: AsyncClient):
        await client.post("/api/erp/assets", json={"name": "Monitor"})
        r = await client.get("/api/erp/assets")
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestErpDashboard:
    async def test_dashboard(self, client: AsyncClient):
        r = await client.get("/api/erp/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "invoices" in data
        assert "expenses" in data
        assert "revenue" in data
        assert "profit" in data
