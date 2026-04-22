"""Cross-cutting tagging — attach tags to any entity via (entity_type, entity_id).

Tags live in their own table; links live in `tag_links`. The `entity_type`
string is whatever slug the caller chooses (e.g. "invoice", "lead"); there is
no referential integrity check against the target table, which keeps this
genuinely polymorphic at the cost of orphan links if an entity is deleted.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acl.resolver import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.tag import Tag, TagLink

router = APIRouter(prefix="/api/tags", tags=["tags"], dependencies=[Depends(get_current_user)])


class TagCreate(BaseModel):
    name: str
    color: str | None = None
    description: str | None = None


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    description: str | None = None


class TagAttach(BaseModel):
    entity_type: str
    entity_id: UUID


def _tag_dict(t: Tag) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "color": t.color,
        "description": t.description,
    }


@router.get("")
async def list_tags(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Tag).order_by(Tag.name))
    return [_tag_dict(t) for t in r.scalars().all()]


@router.post("", status_code=201, dependencies=[Depends(require_permission("admin.tag.manage"))])
async def create_tag(p: TagCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Tag).where(Tag.name == p.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Tag '{p.name}' already exists")
    t = Tag(name=p.name, color=p.color, description=p.description)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _tag_dict(t)


@router.patch("/{tag_id}", dependencies=[Depends(require_permission("admin.tag.manage"))])
async def update_tag(tag_id: UUID, p: TagUpdate, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tag, tag_id)
    if not t:
        raise HTTPException(404, "Tag not found")
    if p.name is not None:
        t.name = p.name
    if p.color is not None:
        t.color = p.color
    if p.description is not None:
        t.description = p.description
    await db.commit()
    return _tag_dict(t)


@router.delete("/{tag_id}", status_code=204, dependencies=[Depends(require_permission("admin.tag.manage"))])
async def delete_tag(tag_id: UUID, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tag, tag_id)
    if not t:
        raise HTTPException(404, "Tag not found")
    await db.delete(t)
    await db.commit()


# ── Attach / detach to entities ─────────────────────────────────────

@router.get("/for")
async def tags_for_entity(
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(Tag, TagLink.id)
        .join(TagLink, TagLink.tag_id == Tag.id)
        .where(TagLink.entity_type == entity_type, TagLink.entity_id == entity_id)
        .order_by(Tag.name)
    )
    rows = r.all()
    return [{**_tag_dict(t), "link_id": str(link_id)} for t, link_id in rows]


@router.post("/{tag_id}/attach", status_code=201, dependencies=[Depends(require_permission("admin.tag.manage"))])
async def attach_tag(tag_id: UUID, p: TagAttach, db: AsyncSession = Depends(get_db)):
    t = await db.get(Tag, tag_id)
    if not t:
        raise HTTPException(404, "Tag not found")
    existing = await db.execute(
        select(TagLink).where(
            TagLink.tag_id == tag_id,
            TagLink.entity_type == p.entity_type,
            TagLink.entity_id == p.entity_id,
        )
    )
    link = existing.scalar_one_or_none()
    if link:
        return {"id": str(link.id), "already": True}
    link = TagLink(tag_id=tag_id, entity_type=p.entity_type, entity_id=p.entity_id)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return {"id": str(link.id)}


@router.delete("/{tag_id}/detach", status_code=204, dependencies=[Depends(require_permission("admin.tag.manage"))])
async def detach_tag(
    tag_id: UUID,
    entity_type: str = Query(...),
    entity_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(TagLink).where(
            and_(
                TagLink.tag_id == tag_id,
                TagLink.entity_type == entity_type,
                TagLink.entity_id == entity_id,
            )
        )
    )
    await db.commit()


@router.get("/entities")
async def entities_with_tag(tag_id: UUID = Query(...), db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(TagLink).where(TagLink.tag_id == tag_id).order_by(TagLink.created_at.desc()).limit(500)
    )
    return [
        {"entity_type": link.entity_type, "entity_id": str(link.entity_id), "created_at": link.created_at.isoformat()}
        for link in r.scalars().all()
    ]
