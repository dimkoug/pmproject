"""Pure-function tests for recent features (no DB / no network).

Covers logic that's easy to regress and security-sensitive:

  * #80 Stripe — webhook signature verification (HMAC + 5-min replay window)
  * #48 SSO   — signed-state token round-trip + tamper detection
  * #72 Automation — condition evaluator + dotted-path resolver
  * #49 Semantic — chunker overlap behaviour + mock embedding determinism
  * #52 AI plan — mock plan shape + key extraction
  * #77 Field masks — apply_field_mask helper
"""

from __future__ import annotations

import time

import pytest


# ─── #80 Stripe webhook signature ────────────────────────────────────


def test_stripe_signature_verifies_correct():
    from app.config import settings
    from app.services.stripe_client import verify_webhook_signature
    settings.stripe_webhook_secret = "whsec_test"
    payload = b'{"type":"checkout.session.completed"}'
    ts = int(time.time())
    import hashlib, hmac as _hmac
    sig = _hmac.new(b"whsec_test", f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    header = f"t={ts},v1={sig}"
    assert verify_webhook_signature(payload, header) is not None


def test_stripe_signature_rejects_tampered_payload():
    from app.config import settings
    from app.services.stripe_client import verify_webhook_signature
    settings.stripe_webhook_secret = "whsec_test"
    payload = b'{"type":"checkout.session.completed"}'
    ts = int(time.time())
    import hashlib, hmac as _hmac
    sig = _hmac.new(b"whsec_test", f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    header = f"t={ts},v1={sig}"
    tampered = b'{"type":"different"}'
    assert verify_webhook_signature(tampered, header) is None


def test_stripe_signature_rejects_old_replay():
    from app.config import settings
    from app.services.stripe_client import verify_webhook_signature
    settings.stripe_webhook_secret = "whsec_test"
    payload = b'{}'
    ts = int(time.time()) - 600  # 10 min ago, beyond 5-min window
    import hashlib, hmac as _hmac
    sig = _hmac.new(b"whsec_test", f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    header = f"t={ts},v1={sig}"
    assert verify_webhook_signature(payload, header) is None


def test_stripe_signature_rejects_missing_secret():
    from app.config import settings
    from app.services.stripe_client import verify_webhook_signature
    settings.stripe_webhook_secret = None
    assert verify_webhook_signature(b"x", "t=123,v1=abc") is None


# ─── #48 SSO state token ─────────────────────────────────────────────


def test_sso_state_round_trips():
    from app.routers.sso import _make_state, _verify_state
    state = _make_state("aaaa-bbbb")
    payload = _verify_state(state)
    assert payload is not None
    assert payload["p"] == "aaaa-bbbb"


def test_sso_state_rejects_tampered_body():
    from app.routers.sso import _make_state, _verify_state
    state = _make_state("aaaa-bbbb")
    body, sig = state.split(".", 1)
    # Flip a char in the body (still base64-decodable but signature won't match)
    tampered_body = body[:-1] + ("a" if body[-1] != "a" else "b")
    assert _verify_state(f"{tampered_body}.{sig}") is None


def test_sso_state_rejects_tampered_sig():
    from app.routers.sso import _make_state, _verify_state
    state = _make_state("aaaa-bbbb")
    body, sig = state.split(".", 1)
    bad_sig = "0" * len(sig)
    assert _verify_state(f"{body}.{bad_sig}") is None


# ─── #72 Automation condition evaluator ──────────────────────────────


def test_automation_condition_resolves_dotted_path():
    from app.services.automation import _resolve_path
    payload = {"after": {"amount": 12500}, "actor_id": "u1"}
    assert _resolve_path(payload, "after.amount") == 12500
    assert _resolve_path(payload, "actor_id") == "u1"
    assert _resolve_path(payload, "after.missing") is None


@pytest.mark.parametrize("op,value,expected", [
    ("==", 100, True),
    ("!=", 99, True),
    (">", 99, True),
    (">=", 100, True),
    ("<", 101, True),
    ("<=", 100, True),
    ("contains", "00", True),
    ("in", [50, 100, 150], True),
    ("exists", None, True),
])
def test_automation_ops_truthy(op, value, expected):
    from app.services.automation import _evaluate_condition
    cond = {"field": "x", "op": op, "value": value}
    assert _evaluate_condition({"x": 100}, cond) is expected


def test_automation_ops_falsy():
    from app.services.automation import _evaluate_condition
    payload = {"x": 100}
    assert _evaluate_condition(payload, {"field": "x", "op": "==", "value": 99}) is False
    assert _evaluate_condition(payload, {"field": "missing", "op": "exists"}) is False
    assert _evaluate_condition(payload, {"field": "x", "op": ">", "value": "not-a-number"}) is False


def test_automation_all_conditions_must_match():
    from app.services.automation import _evaluate_conditions
    payload = {"after": {"amount": 12000, "vendor": "Acme"}}
    assert _evaluate_conditions(payload, [
        {"field": "after.amount", "op": ">", "value": 10000},
        {"field": "after.vendor", "op": "==", "value": "Acme"},
    ]) is True
    assert _evaluate_conditions(payload, [
        {"field": "after.amount", "op": ">", "value": 10000},
        {"field": "after.vendor", "op": "==", "value": "WrongCo"},
    ]) is False
    # No conditions = always match
    assert _evaluate_conditions(payload, []) is True
    assert _evaluate_conditions(payload, None) is True


# ─── #49 Semantic search — chunker + mock embed ──────────────────────


def test_chunker_short_text_one_chunk():
    from app.services.embeddings import chunk_text
    text = "Hello world."
    assert chunk_text(text) == ["Hello world."]


def test_chunker_splits_with_overlap():
    from app.services.embeddings import chunk_text
    text = " ".join(["word"] * 200)  # ~999 chars
    chunks = chunk_text(text, size=200, overlap=40)
    assert len(chunks) >= 4
    # No chunk should exceed size by much
    assert all(len(c) <= 220 for c in chunks)
    # Reconstructed text should contain every original word
    reconstructed = " ".join(chunks).split()
    assert "word" in reconstructed


def test_chunker_empty_input_returns_empty():
    from app.services.embeddings import chunk_text
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_mock_embed_is_deterministic():
    from app.config import settings
    from app.services.embeddings import embed_texts
    settings.llm_api_key = None  # force mock path
    a = embed_texts(["hello world"])[0]
    b = embed_texts(["hello world"])[0]
    assert a == b
    assert len(a) == 1536


def test_mock_embed_similar_for_overlapping_tokens():
    from app.config import settings
    from app.services.embeddings import cosine_similarity, embed_texts
    settings.llm_api_key = None
    near = embed_texts(["payment terms invoice"])[0]
    same = embed_texts(["invoice payment terms"])[0]  # token reorder
    far = embed_texts(["unrelated subject xyzzy"])[0]
    assert cosine_similarity(near, same) > cosine_similarity(near, far)


# ─── #52 AI plan mock ────────────────────────────────────────────────


def test_ai_plan_mock_shape():
    from app.config import settings
    from app.services.llm import generate_project_plan
    settings.llm_api_key = None  # force mock
    plan = generate_project_plan("Build a SaaS HR platform for mid-market customers")
    assert plan["source"] == "mock"
    assert isinstance(plan["tasks"], list) and len(plan["tasks"]) > 0
    assert isinstance(plan["risks"], list) and len(plan["risks"]) > 0
    assert isinstance(plan["deliverables"], list) and len(plan["deliverables"]) > 0
    assert isinstance(plan["milestones"], list) and len(plan["milestones"]) > 0
    # Each task has the expected keys
    for t in plan["tasks"]:
        assert "title" in t
        assert "estimate_hours" in t


def test_ai_plan_mock_branches_on_keyword():
    from app.config import settings
    from app.services.llm import generate_project_plan
    settings.llm_api_key = None
    sw = generate_project_plan("New mobile app launch")
    cn = generate_project_plan("Build a 40-storey tower in downtown")
    sw_titles = " ".join(t["title"] for t in sw["tasks"]).lower()
    cn_titles = " ".join(t["title"] for t in cn["tasks"]).lower()
    assert "implementation" in sw_titles or "deployment" in sw_titles
    assert "structural" in cn_titles or "permits" in cn_titles


# ─── #77 Field masks helper ─────────────────────────────────────────


def test_apply_field_mask_replaces_with_none():
    from app.acl.resolver import apply_field_mask
    row = {"id": "1", "name": "Acme", "annual_revenue": 5_000_000, "industry": "tech"}
    masked = apply_field_mask(row, {"annual_revenue"})
    assert masked["annual_revenue"] is None
    assert masked["name"] == "Acme"
    # Original is untouched
    assert row["annual_revenue"] == 5_000_000


def test_apply_field_mask_empty_mask_is_passthrough():
    from app.acl.resolver import apply_field_mask
    row = {"a": 1, "b": 2}
    out = apply_field_mask(row, set())
    assert out == row


def test_apply_field_mask_ignores_missing_fields():
    from app.acl.resolver import apply_field_mask
    row = {"a": 1}
    out = apply_field_mask(row, {"b", "c"})
    assert out == {"a": 1}
