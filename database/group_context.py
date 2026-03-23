from __future__ import annotations

from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Group, User, UserGroup

VALID_LANGUAGES = {"uz", "ru", "en"}
VALID_THEMES = {"light", "dark"}
VALID_GROUP_ROLES = {"admin", "member"}


def normalize_lang(code: Optional[str]) -> str:
    value = (code or "uz").lower()
    if value.startswith("ru"):
        return "ru"
    if value.startswith("en"):
        return "en"
    return "uz"


def normalize_theme(value: Optional[str]) -> str:
    theme = (value or "light").lower()
    return theme if theme in VALID_THEMES else "light"


def normalize_group_role(role: Optional[str]) -> str:
    value = (role or "member").lower()
    return value if value in VALID_GROUP_ROLES else "member"


def build_default_group_name(user: User, fallback_group_id: Optional[int] = None) -> str:
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    base = full_name or (f"@{user.username}" if user.username else f"Group {fallback_group_id or user.id}")
    return f"{base} Team"


async def ensure_user_setup(db: AsyncSession, user: User) -> User:
    changed = False
    legacy_group_id = int(user.active_group_id or user.group_id or user.id)

    group = (await db.execute(select(Group).where(Group.id == legacy_group_id))).scalar_one_or_none()
    if not group:
        group = Group(
            id=legacy_group_id,
            name=build_default_group_name(user, legacy_group_id),
            created_by=user.id,
        )
        db.add(group)
        await db.flush()

    membership = (
        await db.execute(
            select(UserGroup).where(
                UserGroup.user_id == user.id,
                UserGroup.group_id == group.id,
            )
        )
    ).scalar_one_or_none()
    if not membership:
        membership = UserGroup(
            user_id=user.id,
            group_id=group.id,
            role="admin" if user.is_admin or user.id == legacy_group_id else "member",
        )
        db.add(membership)

    if user.active_group_id != group.id:
        user.active_group_id = group.id
        changed = True
    if user.group_id != group.id:
        user.group_id = group.id
        changed = True

    lang = normalize_lang(user.language_code)
    if user.language_code != lang:
        user.language_code = lang
        changed = True

    theme = normalize_theme(getattr(user, "theme_preference", None))
    if getattr(user, "theme_preference", None) != theme:
        user.theme_preference = theme
        changed = True

    if changed:
        await db.flush()

    return user


async def get_active_group_id(db: AsyncSession, user: User) -> int:
    await ensure_user_setup(db, user)
    return int(user.active_group_id or user.group_id or user.id)


async def get_active_group(db: AsyncSession, user: User) -> Group:
    group_id = await get_active_group_id(db, user)
    group = (await db.execute(select(Group).where(Group.id == group_id))).scalar_one()
    return group


async def list_user_groups(db: AsyncSession, user_id: int) -> list[dict]:
    rows = (
        await db.execute(
            select(UserGroup, Group)
            .join(Group, Group.id == UserGroup.group_id)
            .where(UserGroup.user_id == user_id, Group.is_active.is_(True))
            .order_by(Group.name.asc(), Group.id.asc())
        )
    ).all()
    return [
        {
            "id": group.id,
            "name": group.name,
            "role": membership.role,
            "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
        }
        for membership, group in rows
    ]


async def user_has_group_access(db: AsyncSession, user_id: int, group_id: int) -> bool:
    membership = (
        await db.execute(
            select(UserGroup).where(UserGroup.user_id == user_id, UserGroup.group_id == group_id)
        )
    ).scalar_one_or_none()
    return membership is not None


async def get_group_role(db: AsyncSession, user_id: int, group_id: int) -> Optional[str]:
    membership = (
        await db.execute(
            select(UserGroup).where(UserGroup.user_id == user_id, UserGroup.group_id == group_id)
        )
    ).scalar_one_or_none()
    return membership.role if membership else None


async def is_group_admin(db: AsyncSession, user: User, group_id: Optional[int] = None) -> bool:
    if user.is_admin:
        return True
    resolved_group_id = group_id or await get_active_group_id(db, user)
    role = await get_group_role(db, user.id, resolved_group_id)
    return role == "admin"


async def set_active_group(db: AsyncSession, user: User, group_id: int) -> Group:
    if not await user_has_group_access(db, user.id, group_id):
        raise PermissionError("Group access denied")

    group = (await db.execute(select(Group).where(Group.id == group_id, Group.is_active.is_(True)))).scalar_one_or_none()
    if not group:
        raise ValueError("Group not found")

    user.active_group_id = group_id
    user.group_id = group_id
    await db.flush()
    return group


async def create_group_for_user(
    db: AsyncSession,
    creator: User,
    name: str,
    set_as_active: bool = True,
) -> Group:
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Group name is required")

    group = Group(name=clean_name, created_by=creator.id)
    db.add(group)
    await db.flush()

    db.add(UserGroup(user_id=creator.id, group_id=group.id, role="admin"))
    if set_as_active:
        creator.active_group_id = group.id
        creator.group_id = group.id

    await db.flush()
    return group


async def add_user_to_group(
    db: AsyncSession,
    user: User,
    group_id: int,
    role: str = "member",
) -> UserGroup:
    group = (await db.execute(select(Group).where(Group.id == group_id, Group.is_active.is_(True)))).scalar_one_or_none()
    if not group:
        raise ValueError("Group not found")

    membership = (
        await db.execute(
            select(UserGroup).where(UserGroup.user_id == user.id, UserGroup.group_id == group_id)
        )
    ).scalar_one_or_none()
    if membership:
        membership.role = normalize_group_role(role)
        await db.flush()
        return membership

    membership = UserGroup(user_id=user.id, group_id=group_id, role=normalize_group_role(role))
    db.add(membership)
    await db.flush()

    if not user.active_group_id:
        user.active_group_id = group_id
        user.group_id = group_id
        await db.flush()

    return membership


async def remove_user_from_group(db: AsyncSession, user: User, group_id: int) -> None:
    membership = (
        await db.execute(
            select(UserGroup).where(UserGroup.user_id == user.id, UserGroup.group_id == group_id)
        )
    ).scalar_one_or_none()
    if not membership:
        raise ValueError("Membership not found")

    await db.delete(membership)
    await db.flush()

    if user.active_group_id == group_id:
        next_membership = (
            await db.execute(
                select(UserGroup).where(UserGroup.user_id == user.id).order_by(UserGroup.joined_at.asc())
            )
        ).scalars().first()
        next_group_id = next_membership.group_id if next_membership else None
        user.active_group_id = next_group_id
        user.group_id = next_group_id
        await db.flush()


def group_user_ids_query(group_id: int) -> Select:
    return select(UserGroup.user_id).where(UserGroup.group_id == group_id)


async def ensure_group_membership_for_legacy_user(db: AsyncSession, user: User) -> None:
    await ensure_user_setup(db, user)


async def rename_group(db: AsyncSession, group_id: int, name: str) -> Group:
    group = (await db.execute(select(Group).where(Group.id == group_id, Group.is_active.is_(True)))).scalar_one_or_none()
    if not group:
        raise ValueError("Group not found")
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Group name is required")
    group.name = clean_name
    await db.flush()
    return group


async def deactivate_group(db: AsyncSession, group_id: int) -> None:
    group = (await db.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
    if not group:
        raise ValueError("Group not found")
    group.is_active = False
    await db.flush()

    members = (
        await db.execute(select(User).join(UserGroup, UserGroup.user_id == User.id).where(UserGroup.group_id == group_id))
    ).scalars().all()
    for member in members:
        if member.active_group_id == group_id:
            next_membership = (
                await db.execute(
                    select(UserGroup).where(UserGroup.user_id == member.id, UserGroup.group_id != group_id)
                )
            ).scalars().first()
            next_group_id = next_membership.group_id if next_membership else None
            member.active_group_id = next_group_id
            member.group_id = next_group_id
    await db.flush()
