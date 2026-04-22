"""Onboarding wizard backend (#9).

Tiny surface area:
  * GET  /api/onboarding/status           — current state for the user
  * POST /api/onboarding/steps/{key}      — mark a step complete (idempotent)
  * POST /api/onboarding/skip             — dismiss the wizard entirely
  * POST /api/onboarding/reset            — admin-only; resets for a user

Steps are declared here (not DB-driven) so the frontend and backend stay
in lockstep without a round-trip for catalog.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.cross import WorkspaceMember
from app.models.onboarding import OnboardingProgress
from app.models.project import Project
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"], dependencies=[Depends(get_current_user)])


# Keep this list small and concrete — wizards with 10+ steps get abandoned.
STEPS = [
    {"key": "welcome",     "title": "Welcome",        "description": "Quick intro to the app."},
    {"key": "profile",     "title": "Your profile",   "description": "Confirm your name and timezone."},
    {"key": "workspace",   "title": "Workspace",      "description": "Set up or join a workspace."},
    {"key": "first_project", "title": "First project", "description": "Create a project to explore."},
    {"key": "invite",      "title": "Invite teammates", "description": "Optional — you can do this later."},
]
_STEP_KEYS = {s["key"] for s in STEPS}


async def _get_or_create(db: AsyncSession, user_id) -> OnboardingProgress:
    row = (await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
    )).scalar_one_or_none()
    if row is None:
        row = OnboardingProgress(user_id=user_id, steps_completed="")
        db.add(row); await db.flush()
    return row


def _done_set(row: OnboardingProgress) -> set[str]:
    return {s for s in (row.steps_completed or "").split(",") if s}


async def _status_payload(db: AsyncSession, user: User, row: OnboardingProgress) -> dict:
    done = _done_set(row)
    # Auto-detect completions based on live state so the wizard doesn't demand
    # work the user has already done (e.g. they already have a project).
    has_ws = (await db.execute(
        select(func.count(WorkspaceMember.id)).where(WorkspaceMember.user_id == user.id)
    )).scalar_one() or 0
    has_project = (await db.execute(
        select(func.count(Project.id))
        .where(Project.deleted_at.is_(None))
    )).scalar_one() or 0
    if has_ws > 0:
        done.add("workspace")
    if has_project > 0:
        done.add("first_project")
    row.steps_completed = ",".join(sorted(done))
    return {
        "steps": STEPS,
        "completed": sorted(done),
        "remaining": [s["key"] for s in STEPS if s["key"] not in done],
        "skipped": row.skipped_at is not None,
        "finished": row.completed_at is not None,
        "show_wizard": (row.skipped_at is None and row.completed_at is None
                        and len(done) < len(STEPS)),
    }


@router.get("/status")
async def get_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db, user.id)
    payload = await _status_payload(db, user, row)
    await db.commit()
    return payload


@router.post("/steps/{key}")
async def complete_step(key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if key not in _STEP_KEYS:
        raise HTTPException(400, f"Unknown step: {key}")
    row = await _get_or_create(db, user.id)
    done = _done_set(row)
    done.add(key)
    row.steps_completed = ",".join(sorted(done))
    # When every step is ticked, mark the whole wizard as finished so we stop
    # showing it on subsequent logins.
    if done >= _STEP_KEYS:
        row.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return await _status_payload(db, user, row)


@router.post("/skip")
async def skip_wizard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await _get_or_create(db, user.id)
    row.skipped_at = datetime.now(timezone.utc)
    await db.commit()
    return {"skipped": True}


@router.post("/reset/{user_id}")
async def reset_for_user(user_id: UUID, current: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Admins can re-trigger the wizard for any user (useful for demos)."""
    if current.role != UserRole.ADMIN:
        raise HTTPException(403, "Admin only")
    row = (await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
    )).scalar_one_or_none()
    if row is None:
        return {"reset": True, "no_row": True}
    row.steps_completed = ""
    row.skipped_at = None
    row.completed_at = None
    await db.commit()
    return {"reset": True}
