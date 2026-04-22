"""Invoice/Quote PDF rendering (#1).

Unit tests for:
  * _safe() unicode normalisation
  * _fmt_money() currency handling
  * render_invoice_pdf / render_quote_pdf produce valid PDF bytes
  * Integration via /api/erp/invoices/{id}/pdf + /api/erp/quotes/{id}/pdf
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestSafeNormalization:
    def test_em_and_en_dash_become_ascii_hyphen(self):
        from app.services.pdf_docs import _safe
        assert _safe("a — b") == "a - b"
        assert _safe("a – b") == "a - b"

    def test_smart_quotes_become_straight(self):
        from app.services.pdf_docs import _safe
        assert _safe("don’t “stop”") == "don't \"stop\""

    def test_none_is_empty_string(self):
        from app.services.pdf_docs import _safe
        assert _safe(None) == ""
        assert _safe("") == ""

    def test_unmappable_chars_replaced_not_crashed(self):
        from app.services.pdf_docs import _safe
        # Emoji gets coerced via latin-1 errors="replace" into "?"
        out = _safe("Hello 🚀 world")
        assert "?" in out
        # And doesn't raise.


class TestMoneyFormat:
    def test_usd_uses_dollar_symbol(self):
        from app.services.pdf_docs import _fmt_money
        assert _fmt_money(1234.5, "USD") == "$1,234.50"

    def test_eur_uses_safe_ascii_prefix(self):
        from app.services.pdf_docs import _fmt_money
        # EUR/GBP use word prefixes (not €/£) so they render with core Helvetica.
        assert _fmt_money(100.0, "EUR") == "EUR 100.00"

    def test_unknown_currency_falls_back_to_code(self):
        from app.services.pdf_docs import _fmt_money
        out = _fmt_money(10, "JPY")
        assert out.startswith("JPY ")
        assert "10.00" in out


class TestRenderInvoicePdf:
    def test_produces_valid_pdf_magic(self):
        from app.services.pdf_docs import render_invoice_pdf
        pdf = render_invoice_pdf(
            invoice={
                "invoice_number": "INV-TEST", "invoice_date": "2026-01-01",
                "due_date": "2026-02-01", "status": "sent",
                "subtotal": 100.0, "tax_amount": 10.0, "total_amount": 110.0,
                "notes": "Thank you",
            },
            lines=[{"description": "Widget", "quantity": 2, "unit_price": 50.0, "amount": 100.0}],
            customer={"name": "Acme", "address": "1 Main St"},
            company=None,
            currency="USD",
        )
        assert pdf.startswith(b"%PDF-")
        assert len(pdf) > 500  # non-empty document

    def test_handles_unicode_in_customer_name(self):
        from app.services.pdf_docs import render_invoice_pdf
        # Em-dashes and smart quotes in user-supplied fields must not crash.
        pdf = render_invoice_pdf(
            invoice={"invoice_number": "INV-U", "invoice_date": "2026-01-01",
                     "due_date": None, "status": "draft",
                     "subtotal": 1, "tax_amount": 0, "total_amount": 1,
                     "notes": "Reason — urgent: don’t delay"},
            lines=[{"description": "A — B", "quantity": 1, "unit_price": 1, "amount": 1}],
            customer={"name": "Acmé Ltd", "address": "—"},
            company=None,
            currency="USD",
        )
        assert pdf.startswith(b"%PDF-")


class TestRenderQuotePdf:
    def test_produces_valid_pdf_magic(self):
        from app.services.pdf_docs import render_quote_pdf
        pdf = render_quote_pdf(
            quote={"quote_number": "Q-001", "valid_until": "2026-06-01", "status": "sent",
                   "subtotal": 500, "tax_amount": 0, "total_amount": 500, "terms": "Net 30"},
            lines=[{"description": "Gold Tier", "quantity": 1, "unit_price": 500, "amount": 500}],
            customer={"name": "Foo"}, company=None, currency="USD",
        )
        assert pdf.startswith(b"%PDF-")

    def test_handles_missing_optional_fields(self):
        from app.services.pdf_docs import render_quote_pdf
        pdf = render_quote_pdf(
            quote={"quote_number": "Q-2", "valid_until": None, "status": None,
                   "subtotal": 0, "tax_amount": 0, "total_amount": 0, "terms": None},
            lines=[],
            customer=None, company=None, currency="USD",
        )
        assert pdf.startswith(b"%PDF-")


class TestPdfEndpoints:
    async def test_invoice_pdf_endpoint(self, client: AsyncClient):
        # Create minimal invoice via the real router
        co = (await client.post("/api/crm/companies", json={"name": "PDF Co"})).json()
        inv = (await client.post("/api/erp/invoices", json={
            "invoice_number": "INV-PDF-001",
            "invoice_type": "receivable",
            "company_id": co["id"],
            "items": [{"description": "Consulting", "quantity": 1, "unit_price": 100.0}],
        })).json()
        r = await client.get(f"/api/erp/invoices/{inv['id']}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-"
        assert "invoice-INV-PDF-001.pdf" in r.headers["content-disposition"]

    async def test_invoice_pdf_unknown_id_returns_404(self, client: AsyncClient):
        r = await client.get("/api/erp/invoices/00000000-0000-4000-8000-000000000000/pdf")
        assert r.status_code == 404
