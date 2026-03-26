import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.telegram_auth import verify_telegram_data
from config.admin import check_user_admin_status
from config.settings import settings
from database.finance import normalize_currency
from database.group_context import (
    ensure_user_setup,
    get_active_group_id,
    is_group_admin,
    normalize_lang,
    normalize_theme,
    user_has_group_access,
)
from database.models import User
from database.session import get_db

router = APIRouter()


async def _get_or_create_user(db: AsyncSession, telegram_user: dict) -> User:
    telegram_id = telegram_user.get("id")
    if not telegram_id:
        raise HTTPException(status_code=401, detail="User ID not found in Telegram data")

    result = await db.execute(select(User).where(User.id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=telegram_id,
            username=telegram_user.get("username"),
            first_name=telegram_user.get("first_name") or "User",
            last_name=telegram_user.get("last_name"),
            language_code=normalize_lang(telegram_user.get("language_code")),
            default_currency="UZS",
            theme_preference="light",
        )
        db.add(user)
        await db.flush()
        await ensure_user_setup(db, user)
        await db.commit()
        await db.refresh(user)
        return user

    changed = False
    if user.username != telegram_user.get("username"):
        user.username = telegram_user.get("username")
        changed = True
    if telegram_user.get("first_name") and user.first_name != telegram_user.get("first_name"):
        user.first_name = telegram_user.get("first_name")
        changed = True
    if user.last_name != telegram_user.get("last_name"):
        user.last_name = telegram_user.get("last_name")
        changed = True
    normalized_lang = normalize_lang(user.language_code)
    if user.language_code != normalized_lang:
        user.language_code = normalized_lang
        changed = True
    normalized_theme = normalize_theme(getattr(user, "theme_preference", None))
    if getattr(user, "theme_preference", None) != normalized_theme:
        user.theme_preference = normalized_theme
        changed = True
    normalized_currency = normalize_currency(user.default_currency, "UZS")
    if user.default_currency != normalized_currency:
        user.default_currency = normalized_currency
        changed = True

    await ensure_user_setup(db, user)
    if changed:
        await db.commit()
        await db.refresh(user)
    else:
        await db.flush()

    return user


async def get_current_user(
    request: Request,
    x_telegram_init_data: str = Header(None),
    x_act_as_user: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to resolve the current user from Telegram init data."""
    if not x_telegram_init_data or x_telegram_init_data == "null":
        if not settings.DEBUG:
            raise HTTPException(status_code=401, detail="Missing Telegram init data")

        actor_user = await _get_or_create_user(
            db,
            {
                "id": 123456789,
                "username": "test_user",
                "first_name": "Test",
                "last_name": "User",
                "language_code": "ru",
            },
        )
    else:
        telegram_data = verify_telegram_data(x_telegram_init_data)
        user_json = json.loads(telegram_data.get("user", "{}"))
        actor_user = await _get_or_create_user(db, user_json)

    request.state.actor_user = actor_user
    request.state.effective_user = actor_user
    request.state.is_impersonating = False

    if not x_act_as_user:
        return actor_user

    try:
        target_user_id = int(str(x_act_as_user).strip())
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid impersonation user id")

    if target_user_id == actor_user.id:
        return actor_user

    actor_group_id = await get_active_group_id(db, actor_user)
    global_admin = await check_user_admin_status(actor_user)
    if not global_admin and not await is_group_admin(db, actor_user, actor_group_id):
        raise HTTPException(status_code=403, detail="Impersonation is allowed only for admins")

    target_user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if not global_admin and not await user_has_group_access(db, target_user.id, actor_group_id):
        raise HTTPException(status_code=403, detail="Target user is not available in the current group")

    setattr(target_user, "_impersonated_group_id", actor_group_id)
    setattr(target_user, "_actor_user_id", actor_user.id)
    setattr(
        target_user,
        "_actor_display_name",
        f"{actor_user.first_name or ''} {actor_user.last_name or ''}".strip() or actor_user.username or str(actor_user.id),
    )
    setattr(target_user, "_is_impersonated", True)
    request.state.effective_user = target_user
    request.state.is_impersonating = True
    return target_user


@router.get("/validate")
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validate Telegram init data."""
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "telegram_id": current_user.id,
            "username": current_user.username,
            "first_name": current_user.first_name,
        },
    }
