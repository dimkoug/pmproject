"""Tests for ERP features added in waves v1 and v2.

v1: budgets, currencies/fx, payments/aging, recurring, tax, journal/trial-balance, bank.
v2: inventory, depreciation, credit notes, P&L, balance sheet, cash flow, requisitions.
"""

import pytest
from httpx import AsyncClient


# ── Budgets ─────────────────────────────────────────────────────────

class TestBudgets:
    async def test_create_budget_with_lines(self, client: AsyncClient):
        r = await client.post("/api/erp/budgets", json={
            "name": "Q1 Budget",
            "lines": [
                {"label": "Travel", "category": "travel", "planned_amount": 5000},
                {"label": "Software", "category": "software", "planned_amount": 2000},
            ],
        })
        assert r.status_code == 201
        assert r.json()["total_amount"] == 7000

    async def test_list_budgets(self, client: AsyncClient):
        await client.post("/api/erp/budgets", json={"name": "B1", "lines": []})
        r = await client.get("/api/erp/budgets")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_budget_variance(self, client: AsyncClient):
        b = (await client.post("/api/erp/budgets", json={
            "name": "Var Test",
            "lines": [{"label": "Travel", "category": "travel", "planned_amount": 1000}],
        })).json()
        # Add an expense in the same category
        await client.post("/api/erp/expenses", json={
            "description": "Flight", "amount": 300, "category": "travel",
        })
        r = await client.get(f"/api/erp/budgets/{b['id']}/variance")
        assert r.status_code == 200
        data = r.json()
        assert data["total_planned"] == 1000
        assert data["total_actual"] >= 300
        assert len(data["lines"]) == 1


# ── Currencies & FX ─────────────────────────────────────────────────

class TestCurrency:
    async def test_create_and_list_currencies(self, client: AsyncClient):
        r = await client.post("/api/erp/currencies", json={"code": "EUR", "name": "Euro", "symbol": "€"})
        assert r.status_code == 201
        lst = (await client.get("/api/erp/currencies")).json()
        assert any(c["code"] == "EUR" for c in lst)

    async def test_duplicate_currency_rejected(self, client: AsyncClient):
        await client.post("/api/erp/currencies", json={"code": "GBP", "name": "British Pound"})
        r = await client.post("/api/erp/currencies", json={"code": "GBP", "name": "British Pound"})
        assert r.status_code == 400

    async def test_fx_rate_and_convert(self, client: AsyncClient):
        await client.post("/api/erp/fx-rates", json={"base_code": "USD", "quote_code": "EUR", "rate": 0.9})
        r = await client.get("/api/erp/fx-convert", params={"amount": 100, "from_code": "USD", "to_code": "EUR"})
        assert r.status_code == 200
        assert r.json()["amount"] == 90.0

    async def test_fx_convert_same_currency(self, client: AsyncClient):
        r = await client.get("/api/erp/fx-convert", params={"amount": 50, "from_code": "USD", "to_code": "USD"})
        assert r.status_code == 200
        assert r.json()["rate"] == 1.0

    async def test_fx_convert_no_rate(self, client: AsyncClient):
        r = await client.get("/api/erp/fx-convert", params={"amount": 1, "from_code": "USD", "to_code": "ZZZ"})
        assert r.status_code == 404


# ── Payments & Aging ────────────────────────────────────────────────

class TestPayments:
    async def test_record_payment_updates_paid_amount(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-PAY-1", "subtotal": 1000, "tax_rate": 0,
        })).json()
        r = await client.post("/api/erp/payments", json={"invoice_id": inv["id"], "amount": 400})
        assert r.status_code == 201
        assert r.json()["invoice_paid_amount"] == 400
        assert r.json()["invoice_status"] != "paid"

    async def test_payment_fully_paid_flips_status(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-PAY-2", "subtotal": 500, "tax_rate": 0,
        })).json()
        r = await client.post("/api/erp/payments", json={"invoice_id": inv["id"], "amount": 500})
        assert r.json()["invoice_status"] == "paid"

    async def test_list_payments_for_invoice(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-PAY-3", "subtotal": 100, "tax_rate": 0,
        })).json()
        await client.post("/api/erp/payments", json={"invoice_id": inv["id"], "amount": 50})
        r = await client.get("/api/erp/payments", params={"invoice_id": inv["id"]})
        assert r.status_code == 200
        assert len(r.json()) == 1

    async def test_aging_report(self, client: AsyncClient):
        await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-AGE-1", "subtotal": 200, "tax_rate": 0,
        })
        r = await client.get("/api/erp/invoices/aging")
        assert r.status_code == 200
        assert "buckets" in r.json()


# ── Recurring Invoices ──────────────────────────────────────────────

class TestRecurringInvoices:
    async def test_create_recurring(self, client: AsyncClient):
        r = await client.post("/api/erp/recurring-invoices", json={
            "template_name": "Monthly Retainer", "amount": 5000, "frequency": "monthly",
        })
        assert r.status_code == 201

    async def test_run_recurring_due(self, client: AsyncClient):
        # Create one whose next_run is now (default)
        await client.post("/api/erp/recurring-invoices", json={
            "template_name": "Weekly", "amount": 100, "frequency": "weekly",
        })
        r = await client.post("/api/erp/recurring-invoices/run")
        assert r.status_code == 200
        assert r.json()["count"] >= 1


# ── Tax Report ──────────────────────────────────────────────────────

class TestTaxReport:
    async def test_tax_report_empty(self, client: AsyncClient):
        r = await client.get("/api/erp/reports/tax")
        assert r.status_code == 200
        data = r.json()
        assert "collected" in data and "paid" in data and "net_owed" in data

    async def test_tax_report_with_paid_invoice(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-TAX-1", "subtotal": 1000, "tax_rate": 10,
        })).json()
        await client.patch(f"/api/erp/invoices/{inv['id']}?status=paid")
        r = await client.get("/api/erp/reports/tax")
        assert r.json()["collected"] >= 100


# ── Journal & Trial Balance ─────────────────────────────────────────

class TestJournal:
    async def test_create_balanced_journal(self, client: AsyncClient):
        a1 = (await client.post("/api/erp/accounts", json={"code": "1000", "name": "Cash", "account_type": "asset"})).json()
        a2 = (await client.post("/api/erp/accounts", json={"code": "4000", "name": "Revenue", "account_type": "revenue"})).json()
        r = await client.post("/api/erp/journal", json={
            "entry_number": "J-001",
            "lines": [
                {"account_id": a1["id"], "debit": 100, "credit": 0},
                {"account_id": a2["id"], "debit": 0, "credit": 100},
            ],
        })
        assert r.status_code == 201

    async def test_unbalanced_journal_rejected(self, client: AsyncClient):
        a1 = (await client.post("/api/erp/accounts", json={"code": "1001", "name": "C", "account_type": "asset"})).json()
        r = await client.post("/api/erp/journal", json={
            "entry_number": "J-BAD",
            "lines": [{"account_id": a1["id"], "debit": 100, "credit": 0}],
        })
        assert r.status_code == 400

    async def test_post_journal_updates_balances(self, client: AsyncClient):
        a1 = (await client.post("/api/erp/accounts", json={"code": "1002", "name": "Cash", "account_type": "asset"})).json()
        a2 = (await client.post("/api/erp/accounts", json={"code": "4001", "name": "Rev", "account_type": "revenue"})).json()
        je = (await client.post("/api/erp/journal", json={
            "entry_number": "J-POST",
            "lines": [
                {"account_id": a1["id"], "debit": 250, "credit": 0},
                {"account_id": a2["id"], "debit": 0, "credit": 250},
            ],
        })).json()
        r = await client.post(f"/api/erp/journal/{je['id']}/post")
        assert r.status_code == 200
        assert r.json()["is_posted"] is True
        # Check account balances updated
        accs = (await client.get("/api/erp/accounts")).json()
        cash = next(a for a in accs if a["code"] == "1002")
        rev = next(a for a in accs if a["code"] == "4001")
        assert cash["balance"] == 250
        assert rev["balance"] == 250

    async def test_trial_balance_after_post(self, client: AsyncClient):
        a1 = (await client.post("/api/erp/accounts", json={"code": "1003", "name": "Cash", "account_type": "asset"})).json()
        a2 = (await client.post("/api/erp/accounts", json={"code": "4002", "name": "Rev", "account_type": "revenue"})).json()
        je = (await client.post("/api/erp/journal", json={
            "entry_number": "J-TB",
            "lines": [
                {"account_id": a1["id"], "debit": 500, "credit": 0},
                {"account_id": a2["id"], "debit": 0, "credit": 500},
            ],
        })).json()
        await client.post(f"/api/erp/journal/{je['id']}/post")
        r = await client.get("/api/erp/reports/trial-balance")
        assert r.status_code == 200
        assert r.json()["balanced"] is True


# ── Bank Reconciliation ─────────────────────────────────────────────

class TestBankRecon:
    async def test_create_and_list_bank_txn(self, client: AsyncClient):
        await client.post("/api/erp/bank-transactions", json={"description": "Deposit", "amount": 1000})
        r = await client.get("/api/erp/bank-transactions")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_manual_match(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-BNK", "subtotal": 300, "tax_rate": 0,
        })).json()
        txn = (await client.post("/api/erp/bank-transactions", json={
            "description": "Bank deposit", "amount": 300,
        })).json()
        r = await client.post(f"/api/erp/bank-transactions/{txn['id']}/match",
                               params={"invoice_id": inv["id"]})
        assert r.status_code == 200
        assert r.json()["is_reconciled"] is True

    async def test_auto_match_by_amount(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-AM", "subtotal": 777, "tax_rate": 0,
        })).json()
        await client.post("/api/erp/bank-transactions", json={
            "description": "auto", "amount": 777,
        })
        r = await client.post("/api/erp/bank-transactions/auto-match")
        assert r.status_code == 200
        assert r.json()["matched"] >= 1


# ── v2: Inventory ───────────────────────────────────────────────────

class TestInventory:
    async def test_create_warehouse(self, client: AsyncClient):
        r = await client.post("/api/erp/warehouses", json={"code": "WH1", "name": "Main"})
        assert r.status_code == 201

    async def test_create_product(self, client: AsyncClient):
        r = await client.post("/api/erp/products", json={
            "sku": "SKU-1", "name": "Widget", "unit_cost": 5.0, "unit_price": 10.0,
            "reorder_point": 10, "reorder_qty": 50,
        })
        assert r.status_code == 201

    async def test_stock_movement_and_levels(self, client: AsyncClient):
        w = (await client.post("/api/erp/warehouses", json={"code": "WH-S", "name": "S"})).json()
        p = (await client.post("/api/erp/products", json={
            "sku": "SKU-S", "name": "P", "unit_cost": 1, "unit_price": 2,
            "reorder_point": 5, "reorder_qty": 10,
        })).json()
        # Receive 20
        await client.post("/api/erp/stock/movements", json={
            "product_id": p["id"], "warehouse_id": w["id"],
            "movement_type": "receipt", "quantity": 20,
        })
        # Issue 3
        await client.post("/api/erp/stock/movements", json={
            "product_id": p["id"], "warehouse_id": w["id"],
            "movement_type": "issue", "quantity": 3,
        })
        stock = (await client.get("/api/erp/stock")).json()
        row = next(s for s in stock if s["sku"] == "SKU-S")
        assert row["quantity"] == 17
        assert row["below_reorder"] is False

    async def test_reorder_report_flags_low_stock(self, client: AsyncClient):
        w = (await client.post("/api/erp/warehouses", json={"code": "WH-R", "name": "R"})).json()
        p = (await client.post("/api/erp/products", json={
            "sku": "SKU-R", "name": "P", "unit_cost": 1, "unit_price": 2,
            "reorder_point": 10, "reorder_qty": 100,
        })).json()
        await client.post("/api/erp/stock/movements", json={
            "product_id": p["id"], "warehouse_id": w["id"],
            "movement_type": "receipt", "quantity": 5,
        })
        r = await client.get("/api/erp/stock/reorder")
        assert any(row["sku"] == "SKU-R" for row in r.json())


# ── v2: Depreciation ────────────────────────────────────────────────

class TestDepreciation:
    async def test_create_schedule(self, client: AsyncClient):
        a = (await client.post("/api/erp/assets", json={"name": "Server", "purchase_cost": 12000})).json()
        r = await client.post("/api/erp/depreciation", json={
            "asset_id": a["id"], "useful_life_months": 60, "salvage_value": 0,
            "start_date": "2024-01-01T00:00:00",
        })
        assert r.status_code == 201

    async def test_run_depreciation(self, client: AsyncClient):
        a = (await client.post("/api/erp/assets", json={"name": "Vehicle", "purchase_cost": 30000})).json()
        await client.post("/api/erp/depreciation", json={
            "asset_id": a["id"], "useful_life_months": 60, "salvage_value": 0,
            "start_date": "2024-01-01T00:00:00",
        })
        r = await client.post("/api/erp/depreciation/run", params={"as_of": "2026-01-01T00:00:00"})
        assert r.status_code == 200
        assert r.json()["schedules_posted"] >= 1
        assert r.json()["total_depreciation"] > 0


# ── v2: Credit Notes ────────────────────────────────────────────────

class TestCreditNotes:
    async def test_create_credit_note(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-CN-1", "subtotal": 1000, "tax_rate": 0,
        })).json()
        r = await client.post("/api/erp/credit-notes", json={
            "invoice_id": inv["id"], "cn_number": "CN-1", "amount": 200,
        })
        assert r.status_code == 201

    async def test_credit_exceeds_invoice_rejected(self, client: AsyncClient):
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-CN-2", "subtotal": 100, "tax_rate": 0,
        })).json()
        r = await client.post("/api/erp/credit-notes", json={
            "invoice_id": inv["id"], "cn_number": "CN-2", "amount": 200,
        })
        assert r.status_code == 400


# ── v2: Financial Statements ────────────────────────────────────────

class TestFinancialReports:
    async def test_pnl_report(self, client: AsyncClient):
        r = await client.get("/api/erp/reports/pnl")
        assert r.status_code == 200
        data = r.json()
        for k in ("revenue", "expenses", "net_income", "accounts"):
            assert k in data

    async def test_balance_sheet(self, client: AsyncClient):
        await client.post("/api/erp/accounts", json={"code": "1100", "name": "Bank", "account_type": "asset"})
        await client.post("/api/erp/accounts", json={"code": "2100", "name": "Loans", "account_type": "liability"})
        r = await client.get("/api/erp/reports/balance-sheet")
        assert r.status_code == 200
        data = r.json()
        assert "total_assets" in data and "total_liabilities" in data and "total_equity" in data

    async def test_cash_flow(self, client: AsyncClient):
        r = await client.get("/api/erp/reports/cash-flow", params={"days": 30})
        assert r.status_code == 200
        assert r.json()["horizon_days"] == 30


# ── v2: Requisitions ────────────────────────────────────────────────

class TestRequisitions:
    async def test_create_requisition(self, client: AsyncClient):
        r = await client.post("/api/erp/requisitions", json={
            "req_number": "REQ-1",
            "justification": "Replacement laptops",
            "items": [{"description": "Laptop", "quantity": 2, "unit_price": 1200}],
        })
        assert r.status_code == 201
        assert r.json()["estimated_amount"] == 2400

    async def test_update_status_and_convert_to_po(self, client: AsyncClient):
        v = (await client.post("/api/erp/vendors", json={"name": "Tech Supplier"})).json()
        req = (await client.post("/api/erp/requisitions", json={
            "req_number": "REQ-2",
            "items": [{"description": "Monitor", "quantity": 5, "unit_price": 300}],
        })).json()
        r = await client.patch(f"/api/erp/requisitions/{req['id']}?status=approved")
        assert r.json()["status"] == "approved"
        r2 = await client.post(f"/api/erp/requisitions/{req['id']}/convert",
                                json={"vendor_id": v["id"]})
        assert r2.status_code == 200
        assert "po_id" in r2.json()

    async def test_cannot_convert_unapproved(self, client: AsyncClient):
        v = (await client.post("/api/erp/vendors", json={"name": "V"})).json()
        req = (await client.post("/api/erp/requisitions", json={
            "req_number": "REQ-3",
            "items": [{"description": "x", "quantity": 1, "unit_price": 10}],
        })).json()
        r = await client.post(f"/api/erp/requisitions/{req['id']}/convert",
                               json={"vendor_id": v["id"]})
        assert r.status_code == 400
