import json
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.models import User
from database.finance import normalize_currency
from database.group_context import ensure_user_setup, normalize_lang, normalize_theme
from api.middleware.telegram_auth import verify_telegram_data
from config.settings import settings

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
    x_telegram_init_data: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to resolve the current user from Telegram init data."""
    if not x_telegram_init_data or x_telegram_init_data == "null":
        if not settings.DEBUG:
            raise HTTPException(status_code=401, detail="Missing Telegram init data")

        return await _get_or_create_user(
            db,
            {
                "id": 123456789,
                "username": "test_user",
                "first_name": "Test",
                "last_name": "User",
                "language_code": "ru",
            },
        )

    telegram_data = verify_telegram_data(x_telegram_init_data)
    user_json = json.loads(telegram_data.get("user", "{}"))
    return await _get_or_create_user(db, user_json)


@router.get("/validate")
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validate Telegram init data."""
    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "telegram_id": current_user.id,
            "username": current_user.username,
            "first_name": current_user.first_name
        }
    }
