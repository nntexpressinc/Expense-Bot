from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditLog, User


async def write_audit_log(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    actor: Optional[User] = None,
    group_id: Optional[int] = None,
    payload: Optional[dict[str, Any]] = None,
) -> AuditLog:
    record = AuditLog(
        group_id=group_id,
        actor_user_id=actor.id if actor else None,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        payload=json.dumps(payload, ensure_ascii=False) if payload else None,
    )
    db.add(record)
    await db.flush()
    return record
