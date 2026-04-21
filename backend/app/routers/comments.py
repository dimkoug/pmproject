from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.comment import Comment
from app.models.user import User

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
    await db.commit()
    await db.refresh(comment)
    return {"id": str(comment.id), "body": comment.body, "user_name": current_user.name, "created_at": comment.created_at.isoformat()}


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
