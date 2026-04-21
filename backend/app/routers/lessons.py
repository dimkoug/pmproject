from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.lesson_learned import LessonLearned, LessonCategory
from app.models.user import User

router = APIRouter(prefix="/api/lessons", tags=["lessons"], dependencies=[Depends(get_current_user)])


class LessonCreate(BaseModel):
    project_id: UUID
    title: str
    category: LessonCategory = LessonCategory.OTHER
    what_happened: str
    impact: str | None = None
    recommendation: str | None = None


class LessonRead(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    title: str
    category: str
    what_happened: str
    impact: str | None
    recommendation: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[LessonRead])
async def list_lessons(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LessonLearned).where(LessonLearned.project_id == project_id)
        .order_by(LessonLearned.created_at.desc())
    )
    lessons = result.scalars().all()
    return [
        LessonRead(
            id=l.id, project_id=l.project_id, user_id=l.user_id,
            title=l.title, category=l.category.value,
            what_happened=l.what_happened, impact=l.impact,
            recommendation=l.recommendation, created_at=l.created_at.isoformat(),
        )
        for l in lessons
    ]


@router.post("/", status_code=201)
async def create_lesson(
    payload: LessonCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lesson = LessonLearned(
        project_id=payload.project_id,
        user_id=current_user.id,
        title=payload.title,
        category=payload.category,
        what_happened=payload.what_happened,
        impact=payload.impact,
        recommendation=payload.recommendation,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return {"id": str(lesson.id), "title": lesson.title}


@router.delete("/{lesson_id}", status_code=204)
async def delete_lesson(lesson_id: UUID, db: AsyncSession = Depends(get_db)):
    lesson = await db.get(LessonLearned, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    await db.delete(lesson)
    await db.commit()
