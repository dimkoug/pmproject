"""Pricing rules + discounts (Phase 3 #2).

Covers:
  * apply_discount math (percent/amount/clamping/min_subtotal/none)
  * resolve_unit_price (tier pricing)
  * price_cart end-to-end over real Products
  * DiscountRule time-windowing + redemption cap + code lookup
  * Router CRUD: POST /api/pricing/lists, /api/pricing/discounts, /api/pricing/quote
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestApplyDiscount:
    def test_percent_discount(self):
        from app.services.pricing import apply_discount
        from app.models.pricing import DiscountType
        class R: discount_type, value, min_subtotal = DiscountType.PERCENT, 10, 0
        assert apply_discount(200, R()) == 20.0

    def test_amount_discount(self):
        from app.services.pricing import apply_discount
        from app.models.pricing import DiscountType
        class R: discount_type, value, min_subtotal = DiscountType.AMOUNT, 25, 0
        assert apply_discount(150, R()) == 25

    def test_amount_capped_at_subtotal(self):
        """$500 discount on an $80 cart must not produce a negative total."""
        from app.services.pricing import apply_discount
        from app.models.pricing import DiscountType
        class R: discount_type, value, min_subtotal = DiscountType.AMOUNT, 500, 0
        assert apply_discount(80, R()) == 80

    def test_below_min_subtotal_no_discount(self):
        from app.services.pricing import apply_discount
        from app.models.pricing import DiscountType
        class R: discount_type, value, min_subtotal = DiscountType.AMOUNT, 25, 100
        assert apply_discount(50, R()) == 0.0

    def test_percent_clamped_to_100(self):
        """Defensive — a misconfigured 150% rule must not invert the sign."""
        from app.services.pricing import apply_discount
        from app.models.pricing import DiscountType
        class R: discount_type, value, min_subtotal = DiscountType.PERCENT, 150, 0
        assert apply_discount(100, R()) == 100.0

    def test_none_rule_returns_zero(self):
        from app.services.pricing import apply_discount
        assert apply_discount(100, None) == 0.0


class TestTierPricing:
    async def test_higher_min_quantity_wins(self):
        from tests.conftest import async_session_test
        from app.models.erp import Product
        from app.models.pricing import PriceList, PriceListItem
        from app.services.pricing import resolve_unit_price

        async with async_session_test() as db:
            prod = Product(sku="TIER-A", name="Tier A", unit_price=10.0)
            pl = PriceList(name="Wholesale", currency="USD")
            db.add_all([prod, pl]); await db.commit()
            await db.refresh(prod); await db.refresh(pl)
            db.add(PriceListItem(price_list_id=pl.id, product_id=prod.id, unit_price=9.0, min_quantity=1))
            db.add(PriceListItem(price_list_id=pl.id, product_id=prod.id, unit_price=7.0, min_quantity=10))
            db.add(PriceListItem(price_list_id=pl.id, product_id=prod.id, unit_price=5.0, min_quantity=100))
            await db.commit()

            # qty 5 -> 9.0; qty 15 -> 7.0; qty 500 -> 5.0
            assert await resolve_unit_price(db, prod, pl.id, 5) == 9.0
            assert await resolve_unit_price(db, prod, pl.id, 15) == 7.0
            assert await resolve_unit_price(db, prod, pl.id, 500) == 5.0

    async def test_no_price_list_uses_base_price(self):
        from tests.conftest import async_session_test
        from app.models.erp import Product
        from app.services.pricing import resolve_unit_price
        async with async_session_test() as db:
            prod = Product(sku="BASE-ONLY", name="X", unit_price=42.0)
            db.add(prod); await db.commit(); await db.refresh(prod)
            assert await resolve_unit_price(db, prod, None, 10) == 42.0


class TestLookupDiscount:
    async def test_expired_rule_not_returned(self):
        from tests.conftest import async_session_test
        from app.models.pricing import DiscountRule, DiscountType
        from app.services.pricing import lookup_discount
        async with async_session_test() as db:
            db.add(DiscountRule(
                name="Summer", code="SUMMER",
                discount_type=DiscountType.PERCENT, value=20,
                starts_at=datetime.utcnow() - timedelta(days=60),
                ends_at=datetime.utcnow() - timedelta(days=30),  # expired
            ))
            await db.commit()
            rule = await lookup_discount(db, "SUMMER")
        assert rule is None

    async def test_redemption_cap_excludes_rule(self):
        from tests.conftest import async_session_test
        from app.models.pricing import DiscountRule, DiscountType
        from app.services.pricing import lookup_discount
        async with async_session_test() as db:
            db.add(DiscountRule(
                name="One-off", code="ONEOFF",
                discount_type=DiscountType.AMOUNT, value=5,
                max_redemptions=1, redemptions=1,
            ))
            await db.commit()
            assert await lookup_discount(db, "ONEOFF") is None

    async def test_auto_apply_no_code_returns_code_null_rule(self):
        from tests.conftest import async_session_test
        from app.models.pricing import DiscountRule, DiscountType
        from app.services.pricing import lookup_discount
        async with async_session_test() as db:
            db.add(DiscountRule(
                name="Site-wide", code=None,
                discount_type=DiscountType.PERCENT, value=5,
            ))
            await db.commit()
            rule = await lookup_discount(db, None)
        assert rule is not None and rule.name == "Site-wide"


class TestPriceCart:
    async def test_cart_adds_up_subtotal_and_applies_discount(self):
        from tests.conftest import async_session_test
        from app.models.erp import Product
        from app.models.pricing import DiscountRule, DiscountType
        from app.services.pricing import price_cart
        async with async_session_test() as db:
            p1 = Product(sku="A", name="A", unit_price=10.0)
            p2 = Product(sku="B", name="B", unit_price=25.0)
            db.add_all([p1, p2])
            db.add(DiscountRule(
                name="10off", code="TEN",
                discount_type=DiscountType.PERCENT, value=10,
            ))
            await db.commit()
            await db.refresh(p1); await db.refresh(p2)
            result = await price_cart(db, [
                {"product_id": p1.id, "quantity": 2},
                {"product_id": p2.id, "quantity": 1},
            ], coupon_code="TEN")
        # 2*10 + 1*25 = 45, -10% = 4.5, total = 40.5
        assert result["subtotal"] == 45.0
        assert result["discount"] == 4.5
        assert result["total"] == 40.5
        assert result["discount_label"] == "10off"
        assert len(result["lines"]) == 2

    async def test_unknown_product_is_skipped(self):
        from tests.conftest import async_session_test
        from app.services.pricing import price_cart
        import uuid
        async with async_session_test() as db:
            result = await price_cart(db, [{"product_id": uuid.uuid4(), "quantity": 1}])
        assert result["lines"] == []
        assert result["total"] == 0.0


class TestPricingRouter:
    async def test_create_price_list(self, client: AsyncClient):
        r = await client.post("/api/pricing/lists", json={"name": "Retail", "currency": "USD"})
        assert r.status_code == 201
        assert r.json()["name"] == "Retail"

    async def test_create_discount_and_quote_cart(self, client: AsyncClient):
        # Create a product via the real router
        p = (await client.post("/api/erp/products", json={
            "sku": "RT-1", "name": "Ruffle", "unit_price": 20.0,
        })).json()
        await client.post("/api/pricing/discounts", json={
            "name": "Spring", "code": "SPRING", "discount_type": "percent",
            "value": 15, "min_subtotal": 0,
        })
        r = await client.post("/api/pricing/quote", json={
            "items": [{"product_id": p["id"], "quantity": 3}],
            "coupon_code": "SPRING",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["subtotal"] == 60.0
        assert body["discount"] == 9.0
        assert body["total"] == 51.0

    async def test_quote_with_no_coupon_has_zero_discount(self, client: AsyncClient):
        p = (await client.post("/api/erp/products", json={
            "sku": "RT-2", "name": "Bolt", "unit_price": 4.0,
        })).json()
        r = await client.post("/api/pricing/quote", json={
            "items": [{"product_id": p["id"], "quantity": 5}],
        })
        body = r.json()
        assert body["discount"] == 0.0
        assert body["total"] == 20.0
