import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.user import User

# Matches @name or @first.last — words-with-dots after an @ sign
_MENTION_RE = re.compile(r"@([A-Za-z0-9._-]+)")


async def _resolve_mentions(db: AsyncSession, body: str, actor: User, exclude_self: bool = True) -> list[User]:
    """Find all @handles in `body` and return matching User rows. A handle
    matches either the part before @ in email (e.g. @alice for alice@x.com)
    or the user's name (dot-separated)."""
    handles = set(_MENTION_RE.findall(body))
    if not handles: return []
    matched: list[User] = []
    # Normalise handles for loose comparison
    norm_handles = {h.lower() for h in handles}
    rows = (await db.scalars(select(User).where(User.is_active == True))).all()  # noqa: E712
    for u in rows:
        if exclude_self and u.id == actor.id:
            continue
        email_local = (u.email or "").split("@", 1)[0].lower()
        name_slug = (u.name or "").lower().replace(" ", ".")
        if email_local in norm_handles or name_slug in norm_handles:
            matched.append(u)
    return matched

router = APIRouter(prefix="/api/comments", tags=["comments"], dependencies=[Depends(get_current_user)])


class CommentCreate(BaseModel):
    project_id: UUID
    target_type: str  # task, risk, deliverable, project
    target_id: UUID
    body: str


class CommentRead(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    user_name: str | None = None
    target_type: str
    target_id: UUID
    body: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[CommentRead])
async def list_comments(
    target_type: str,
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Comment, User.name)
        .join(User, Comment.user_id == User.id, isouter=True)
        .where(Comment.target_type == target_type, Comment.target_id == target_id)
        .order_by(Comment.created_at.desc())
        .limit(100)
    )
    rows = result.all()
    return [
        CommentRead(
            id=c.id, project_id=c.project_id, user_id=c.user_id,
            user_name=name, target_type=c.target_type, target_id=c.target_id,
            body=c.body, created_at=c.created_at.isoformat(),
        )
        for c, name in rows
    ]


@router.post("/", status_code=201)
async def create_comment(
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment = Comment(
        project_id=payload.project_id,
        user_id=current_user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        body=payload.body,
    )
    db.add(comment)

    # Create in-app notifications for each @mentioned user + email them
    mentioned = await _resolve_mentions(db, payload.body, current_user)
    link = f"/projects/{payload.project_id}/{payload.target_type}s"
    for m in mentioned:
        db.add(Notification(
            user_id=m.id,
            project_id=payload.project_id,
            title=f"{current_user.name} mentioned you",
            body=payload.body[:280],
            link=link,
        ))
        if m.email:
            from app.services.email import queue_mention_notification
            queue_mention_notification(m.email, current_user.name, f"a comment on {payload.target_type}", link)

    await db.commit()
    await db.refresh(comment)
    return {
        "id": str(comment.id), "body": comment.body, "user_name": current_user.name,
        "created_at": comment.created_at.isoformat(),
        "mentioned_user_ids": [str(m.id) for m in mentioned],
    }


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment = await db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role.value not in ("admin", "project_manager"):
        raise HTTPException(status_code=403, detail="Can only delete your own comments")
    await db.delete(comment)
    await db.commit()
