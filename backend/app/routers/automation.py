"""Automation rules CRUD + run history + dry-run test."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.automation import AutomationRule, AutomationRuleRun
from app.models.user import User
from app.services.automation import (
    SUPPORTED_ACTIONS,
    SUPPORTED_EVENTS,
    SUPPORTED_OPS,
    fire_event,
)

router = APIRouter(prefix="/api/automation", tags=["automation"], dependencies=[Depends(get_current_user)])


class Condition(BaseModel):
    field: str
    op: str
    value: object | None = None


class Action(BaseModel):
    type: str
    params: dict | None = None


class AutomationRuleCreate(BaseModel):
    name: str
    description: str | None = None
    trigger_event: str
    conditions: list[Condition] = []
    actions: list[Action]
    is_active: bool = True


class AutomationRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_event: str | None = None
    conditions: list[Condition] | None = None
    actions: list[Action] | None = None
    is_active: bool | None = None


def _rule_dict(r: AutomationRule) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "description": r.description,
        "trigger_event": r.trigger_event,
        "conditions": r.conditions or [],
        "actions": r.actions or [],
        "is_active": r.is_active,
        "created_by_user_id": str(r.created_by_user_id) if r.created_by_user_id else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("/catalog")
async def get_catalog():
    return {
        "events": SUPPORTED_EVENTS,
        "ops": SUPPORTED_OPS,
        "actions": SUPPORTED_ACTIONS,
    }


@router.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(AutomationRule).order_by(AutomationRule.name))
    return [_rule_dict(rule) for rule in r.scalars().all()]


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return _rule_dict(rule)


@router.post("/rules", status_code=201, dependencies=[Depends(require_permission("admin.automation.manage"))])
async def create_rule(p: AutomationRuleCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if p.trigger_event not in [e["value"] for e in SUPPORTED_EVENTS]:
        raise HTTPException(400, f"Unknown trigger event: {p.trigger_event}")
    for action in p.actions:
        if action.type not in [a["value"] for a in SUPPORTED_ACTIONS]:
            raise HTTPException(400, f"Unknown action type: {action.type}")
    for cond in p.conditions:
        if cond.op not in SUPPORTED_OPS:
            raise HTTPException(400, f"Unknown op: {cond.op}")
    rule = AutomationRule(
        name=p.name,
        description=p.description,
        trigger_event=p.trigger_event,
        conditions=[c.model_dump() for c in p.conditions],
        actions=[a.model_dump() for a in p.actions],
        is_active=p.is_active,
        created_by_user_id=current_user.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_dict(rule)


@router.patch("/rules/{rule_id}", dependencies=[Depends(require_permission("admin.automation.manage"))])
async def update_rule(rule_id: UUID, p: AutomationRuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    if p.name is not None:
        rule.name = p.name
    if p.description is not None:
        rule.description = p.description
    if p.trigger_event is not None:
        rule.trigger_event = p.trigger_event
    if p.conditions is not None:
        rule.conditions = [c.model_dump() for c in p.conditions]
    if p.actions is not None:
        rule.actions = [a.model_dump() for a in p.actions]
    if p.is_active is not None:
        rule.is_active = p.is_active
    await db.commit()
    await db.refresh(rule)
    return _rule_dict(rule)


@router.delete("/rules/{rule_id}", status_code=204, dependencies=[Depends(require_permission("admin.automation.manage"))])
async def delete_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()


class RuleTest(BaseModel):
    payload: dict


@router.post("/rules/{rule_id}/test", dependencies=[Depends(require_permission("admin.automation.manage"))])
async def test_rule(rule_id: UUID, p: RuleTest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rule = await db.get(AutomationRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    fired = await fire_event(db, rule.trigger_event, p.payload, current_user)
    await db.commit()
    return {"fired": fired, "trigger_event": rule.trigger_event}


@router.get("/runs")
async def list_runs(
    rule_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    q = select(AutomationRuleRun).order_by(AutomationRuleRun.triggered_at.desc()).limit(limit)
    if rule_id:
        q = q.where(AutomationRuleRun.rule_id == rule_id)
    r = await db.execute(q)
    return [{
        "id": str(run.id),
        "rule_id": str(run.rule_id),
        "triggered_at": run.triggered_at.isoformat() if run.triggered_at else None,
        "event": run.event,
        "payload": run.payload,
        "actions_run": run.actions_run,
        "actions_failed": run.actions_failed,
        "status": run.status,
        "error": run.error,
    } for run in r.scalars().all()]
