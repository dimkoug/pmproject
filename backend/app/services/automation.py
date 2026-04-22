"""Automation rule evaluator.

`fire_event(db, event, payload, actor)` is the single entry point — call it
after any state change you want rules to react to. The evaluator is best-effort:
exceptions in conditions or actions are swallowed and logged to
`automation_rule_runs.error` so a misconfigured rule never crashes the parent
request.

Adding a new event:
    1. Add to `SUPPORTED_EVENTS` so the rule-builder UI shows it.
    2. Call `fire_event(db, "your.event", payload={...})` from the relevant router.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import AutomationRule, AutomationRuleRun
from app.models.notification import Notification
from app.models.tag import Tag, TagLink
from app.models.user import User

logger = logging.getLogger(__name__)


# Catalog of supported trigger events — the rule-builder UI reads this so
# users can pick from a dropdown rather than typing free strings.
SUPPORTED_EVENTS: list[dict[str, str]] = [
    {"value": "invoice.created", "label": "Invoice created"},
    {"value": "invoice.paid", "label": "Invoice marked paid"},
    {"value": "invoice.status_changed", "label": "Invoice status changed"},
    {"value": "expense.submitted", "label": "Expense submitted"},
    {"value": "expense.approved", "label": "Expense approved"},
    {"value": "lead.created", "label": "Lead created"},
    {"value": "lead.status_changed", "label": "Lead status changed"},
    {"value": "opportunity.stage_changed", "label": "Opportunity stage changed"},
    {"value": "task.created", "label": "Task created"},
    {"value": "task.completed", "label": "Task completed"},
    {"value": "document.uploaded", "label": "Document uploaded"},
    {"value": "sales_order.created", "label": "Sales order created"},
    {"value": "sales_order.invoiced", "label": "Sales order invoiced"},
]

SUPPORTED_OPS: list[str] = ["==", "!=", ">", ">=", "<", "<=", "contains", "in", "exists"]

SUPPORTED_ACTIONS: list[dict[str, str]] = [
    {"value": "notify_user", "label": "Notify a user"},
    {"value": "add_tag", "label": "Attach a tag"},
    {"value": "post_webhook", "label": "POST to a URL"},
    {"value": "log", "label": "Write a log line"},
]


def _resolve_path(payload: dict, path: str) -> Any:
    """Resolve a dotted path like 'invoice.amount' against payload."""
    cur: Any = payload
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _evaluate_condition(payload: dict, cond: dict) -> bool:
    field = cond.get("field")
    op = cond.get("op")
    expected = cond.get("value")
    if not field or not op:
        return False
    actual = _resolve_path(payload, field)
    try:
        if op == "exists":
            return actual is not None
        if op == "==":
            return actual == expected
        if op == "!=":
            return actual != expected
        if op == ">":
            return actual is not None and float(actual) > float(expected)
        if op == ">=":
            return actual is not None and float(actual) >= float(expected)
        if op == "<":
            return actual is not None and float(actual) < float(expected)
        if op == "<=":
            return actual is not None and float(actual) <= float(expected)
        if op == "contains":
            return expected is not None and str(expected).lower() in str(actual or "").lower()
        if op == "in":
            return isinstance(expected, list) and actual in expected
    except Exception:
        return False
    return False


def _evaluate_conditions(payload: dict, conditions: list[dict] | None) -> bool:
    if not conditions:
        return True
    return all(_evaluate_condition(payload, c) for c in conditions)


# ── Action runners ──────────────────────────────────────────────────

async def _action_notify_user(db: AsyncSession, params: dict, payload: dict) -> None:
    user_id = params.get("user_id")
    if not user_id:
        raise ValueError("notify_user requires user_id")
    title = (params.get("title") or "Automation alert").format(**_flat(payload))
    body = (params.get("body") or "").format(**_flat(payload)) or None
    n = Notification(user_id=UUID(str(user_id)), title=title, body=body)
    db.add(n)


async def _action_add_tag(db: AsyncSession, params: dict, payload: dict) -> None:
    tag_id = params.get("tag_id")
    entity_type = params.get("entity_type") or _resolve_path(payload, "entity_type")
    entity_id = params.get("entity_id") or _resolve_path(payload, "entity_id")
    if not (tag_id and entity_type and entity_id):
        raise ValueError("add_tag requires tag_id + entity_type + entity_id")
    # Skip if already attached
    existing = await db.execute(
        select(TagLink).where(
            TagLink.tag_id == UUID(str(tag_id)),
            TagLink.entity_type == entity_type,
            TagLink.entity_id == UUID(str(entity_id)),
        )
    )
    if existing.scalar_one_or_none():
        return
    db.add(TagLink(tag_id=UUID(str(tag_id)), entity_type=entity_type, entity_id=UUID(str(entity_id))))


async def _action_post_webhook(db: AsyncSession, params: dict, payload: dict) -> None:
    url = params.get("url")
    if not url:
        raise ValueError("post_webhook requires url")
    # Use the existing webhook delivery infrastructure if available; otherwise
    # write a placeholder log row. For now we only stash the intent — the
    # cross.WebhookDelivery worker can be expanded later.
    logger.info("automation: would POST to %s with payload keys=%s", url, list(payload.keys()))


async def _action_log(db: AsyncSession, params: dict, payload: dict) -> None:
    msg = (params.get("message") or "automation event").format(**_flat(payload))
    logger.info("automation rule: %s | payload=%s", msg, json.dumps(payload, default=str)[:500])


def _flat(payload: dict) -> dict:
    """Flatten one level for str.format()."""
    flat = {}
    for k, v in (payload or {}).items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                flat[f"{k}_{k2}"] = v2
        else:
            flat[k] = v
    return flat


_ACTION_RUNNERS = {
    "notify_user": _action_notify_user,
    "add_tag": _action_add_tag,
    "post_webhook": _action_post_webhook,
    "log": _action_log,
}


# ── Public entry point ──────────────────────────────────────────────

async def fire_event(
    db: AsyncSession,
    event: str,
    payload: dict[str, Any] | None = None,
    actor: User | None = None,
) -> int:
    """Run all active rules for this event. Returns the number of rules fired."""
    payload = payload or {}
    try:
        result = await db.execute(
            select(AutomationRule).where(
                AutomationRule.trigger_event == event,
                AutomationRule.is_active == True,  # noqa: E712
            )
        )
        rules = result.scalars().all()
    except Exception:
        logger.warning("automation: failed to load rules for %s", event, exc_info=True)
        return 0

    fired = 0
    for rule in rules:
        try:
            if not _evaluate_conditions(payload, rule.conditions):
                continue
            actions_run = 0
            actions_failed = 0
            errors: list[str] = []
            for action in rule.actions or []:
                kind = action.get("type")
                runner = _ACTION_RUNNERS.get(kind)
                if not runner:
                    actions_failed += 1
                    errors.append(f"unknown action: {kind}")
                    continue
                try:
                    await runner(db, action.get("params") or {}, payload)
                    actions_run += 1
                except Exception as e:
                    actions_failed += 1
                    errors.append(f"{kind}: {e}")
                    logger.warning("automation action %s failed for rule %s", kind, rule.name, exc_info=True)
            status = (
                "skipped"
                if actions_run == 0 and actions_failed == 0
                else "failed"
                if actions_run == 0
                else "partial"
                if actions_failed
                else "success"
            )
            db.add(AutomationRuleRun(
                rule_id=rule.id,
                event=event,
                payload=payload,
                actions_run=actions_run,
                actions_failed=actions_failed,
                status=status,
                error="\n".join(errors)[:1000] if errors else None,
            ))
            fired += 1
        except Exception:
            logger.warning("automation: rule %s evaluation failed", rule.name, exc_info=True)
    return fired
