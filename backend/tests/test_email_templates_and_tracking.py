"""Email templates (#6) + open/click tracking (#7).

Covers:
  * render_template override behavior + placeholder substitution
  * admin CRUD on templates
  * open pixel returns GIF bytes and records an event
  * click redirect returns 302 to target URL and records an event
  * tracking stats aggregates by template_key and event_type
  * _track_html() rewrites links + appends pixel
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRenderTemplate:
    def test_uses_defaults_when_db_has_no_override(self):
        from app.services.email import render_template
        subj, text, html = render_template(
            "nonexistent_key", "Default Subject", "Hello {name}", "<b>Hi {name}</b>", {"name": "Ada"}
        )
        assert subj == "Default Subject"
        assert text == "Hello Ada"
        assert html == "<b>Hi Ada</b>"

    def test_missing_placeholder_renders_as_empty_string(self):
        from app.services.email import render_template
        subj, text, _html = render_template(
            "nop", "S", "Hi {who}", None, {}
        )
        # {who} isn't in ctx; our _D()[__missing__] returns "" so no crash.
        assert "Hi" in text
        assert "{who}" not in text


class TestTrackHtmlRewriting:
    def test_links_are_rewritten_through_click_endpoint(self):
        from app.services.email import _track_html
        html = '<a href="https://example.com/foo">click</a>'
        result = _track_html(html, "user@x.com", "password_reset")
        assert "/api/t/click/" in result
        # Original URL is URL-encoded in the u= param
        assert "example.com" in result

    def test_open_pixel_is_appended(self):
        from app.services.email import _track_html
        html = "<p>hi</p>"
        result = _track_html(html, "user@x.com", "welcome")
        assert "/api/t/open/" in result
        assert "img" in result.lower()

    def test_empty_html_passes_through(self):
        from app.services.email import _track_html
        assert _track_html("", "u@x", "k") == ""


class TestTrackingEndpoints:
    async def test_open_pixel_serves_gif_bytes(self, client: AsyncClient):
        r = await client.get("/api/t/open/evt123.gif?r=bob@x.com&k=welcome")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/gif"
        # GIF89a magic bytes at file start
        assert r.content[:6] in (b"GIF89a", b"GIF87a")
        # Cache-busted so proxies don't swallow repeated opens
        assert "no-store" in r.headers.get("cache-control", "")

    async def test_click_redirects_to_target(self, client: AsyncClient):
        r = await client.get(
            "/api/t/click/evt999?r=bob@x.com&k=welcome&u=https://example.com/dest",
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"] == "https://example.com/dest"

    async def test_click_records_event_in_db(self, client: AsyncClient):
        from tests.conftest import async_session_test
        from sqlalchemy import select
        from app.models.notification import EmailTrackingEvent
        await client.get(
            "/api/t/click/evt888?r=track@x.com&k=signature_request&u=https://y.com",
            follow_redirects=False,
        )
        async with async_session_test() as db:
            rows = (await db.execute(
                select(EmailTrackingEvent).where(EmailTrackingEvent.recipient == "track@x.com")
            )).scalars().all()
        events = [(r.event_type, r.template_key, r.url) for r in rows]
        assert ("click", "signature_request", "https://y.com") in events

    async def test_stats_aggregates_by_template_and_event(self, client: AsyncClient):
        # Seed: 2 opens, 1 click for key "newsletter"; 1 open for "welcome"
        await client.get("/api/t/open/a.gif?r=u1@x&k=newsletter")
        await client.get("/api/t/open/b.gif?r=u2@x&k=newsletter")
        await client.get("/api/t/click/c?r=u3@x&k=newsletter&u=https://z")
        await client.get("/api/t/open/d.gif?r=u4@x&k=welcome")

        r = await client.get("/api/t/stats")
        assert r.status_code == 200
        stats = r.json()
        assert stats["newsletter"]["open"] >= 2
        assert stats["newsletter"]["click"] >= 1
        assert stats["welcome"]["open"] >= 1


class TestTemplateAdminCrud:
    async def test_create_and_get_template(self, client: AsyncClient):
        r = await client.post("/api/admin/email-templates", json={
            "key": "custom_promo",
            "subject": "Special offer for {name}",
            "body_text": "Hi {name}, try us!",
            "body_html": "<p>Hi {name}</p>",
        })
        assert r.status_code == 201
        r2 = await client.get("/api/admin/email-templates/custom_promo")
        assert r2.status_code == 200
        body = r2.json()
        assert body["subject"] == "Special offer for {name}"
        assert body["body_html"] == "<p>Hi {name}</p>"

    async def test_duplicate_key_rejected(self, client: AsyncClient):
        await client.post("/api/admin/email-templates", json={
            "key": "dup_key", "subject": "s", "body_text": "t",
        })
        r = await client.post("/api/admin/email-templates", json={
            "key": "dup_key", "subject": "s2", "body_text": "t2",
        })
        assert r.status_code == 400

    async def test_list_returns_all(self, client: AsyncClient):
        await client.post("/api/admin/email-templates", json={
            "key": "list_a", "subject": "a", "body_text": "a",
        })
        await client.post("/api/admin/email-templates", json={
            "key": "list_b", "subject": "b", "body_text": "b",
        })
        r = await client.get("/api/admin/email-templates")
        keys = {t["key"] for t in r.json()}
        assert "list_a" in keys and "list_b" in keys

    async def test_update_template(self, client: AsyncClient):
        created = await client.post("/api/admin/email-templates", json={
            "key": "edit_me", "subject": "old", "body_text": "old",
        })
        tid = created.json()["id"]
        r = await client.patch(f"/api/admin/email-templates/{tid}", json={
            "key": "edit_me", "subject": "new", "body_text": "new body", "body_html": "<b>new</b>",
        })
        assert r.status_code == 200
        latest = await client.get("/api/admin/email-templates/edit_me")
        assert latest.json()["subject"] == "new"
        assert latest.json()["body_html"] == "<b>new</b>"

    async def test_delete_template(self, client: AsyncClient):
        created = await client.post("/api/admin/email-templates", json={
            "key": "gone_soon", "subject": "s", "body_text": "t",
        })
        tid = created.json()["id"]
        r = await client.delete(f"/api/admin/email-templates/{tid}")
        assert r.status_code == 204
        r2 = await client.get("/api/admin/email-templates/gone_soon")
        assert r2.status_code == 404

    async def test_get_unknown_key_is_404(self, client: AsyncClient):
        r = await client.get("/api/admin/email-templates/does_not_exist")
        assert r.status_code == 404
