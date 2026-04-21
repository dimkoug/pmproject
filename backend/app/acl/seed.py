"""Seed the ACL catalog at application startup.

Idempotent — safe to run on every boot. Upserts permissions by codename,
upserts system groups by name, and rebuilds each system group's permission
set from the catalog. User-created groups are never touched.
"""

import logging

from sqlalchemy import delete, select, text

from app.acl.catalog import CATALOG, DEFAULT_GROUPS
from app.database import async_session
from app.models.acl import Group, Permission, group_permissions

logger = logging.getLogger(__name__)

# Arbitrary but stable int for pg_advisory_xact_lock — prevents concurrent
# backend replicas from both running the seed at once (race on the DELETE +
# INSERT pattern below). Lock is released at transaction end.
_SEED_LOCK_KEY = 73126901


async def seed_acl() -> None:
    """Upsert permissions and refresh system groups. Safe to call from multiple replicas."""
    async with async_session() as db:
        # Serialize seed work across replicas. The lock is held until commit/rollback.
        await db.execute(text("SELECT pg_advisory_xact_lock(:k)").bindparams(k=_SEED_LOCK_KEY))
        # 1. Upsert permissions by codename
        existing = {
            p.codename: p
            for p in (await db.scalars(select(Permission))).all()
        }
        for spec in CATALOG:
            perm = existing.get(spec.codename)
            if perm is None:
                perm = Permission(
                    codename=spec.codename,
                    name=spec.name,
                    description=spec.description,
                    category=spec.category,
                )
                db.add(perm)
            else:
                # Keep name / description / category current with the catalog
                perm.name = spec.name
                perm.description = spec.description
                perm.category = spec.category
        await db.flush()

        # Re-read permissions now that new ones are in
        perms_by_code = {
            p.codename: p
            for p in (await db.scalars(select(Permission))).all()
        }

        # 2. Upsert system groups and refresh their permission membership
        groups = {g.name: g for g in (await db.scalars(select(Group))).all()}
        for name, description, codenames in DEFAULT_GROUPS:
            group = groups.get(name)
            if group is None:
                group = Group(name=name, description=description, is_system=True)
                db.add(group)
                await db.flush()
            else:
                group.is_system = True
                group.description = description

            # Rebuild membership: delete existing links for this group, add the
            # current catalog set. User-edited group perms are preserved only
            # for non-system groups (which we don't touch here at all).
            await db.execute(
                delete(group_permissions).where(group_permissions.c.group_id == group.id)
            )
            for code in codenames:
                p = perms_by_code.get(code)
                if p is None:
                    logger.warning("ACL seed: group %r references missing codename %r", name, code)
                    continue
                await db.execute(
                    group_permissions.insert().values(group_id=group.id, permission_id=p.id)
                )

        await db.commit()
    logger.info("ACL seeded: %d permissions, %d system groups", len(CATALOG), len(DEFAULT_GROUPS))
