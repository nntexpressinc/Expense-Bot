"""
Admin utilities and helpers
"""
from typing import Optional
from config.settings import settings
from database.models import User


def is_user_admin(user_id: int) -> bool:
    """
    Check if user is admin by ID from environment variable
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True if user is admin
    """
    return user_id in settings.admin_ids


async def check_user_admin_status(user: User) -> bool:
    """
    Check if user is admin (from env or database)
    
    Priority:
    1. Check .env ADMIN_USER_IDS
    2. Check database is_admin flag
    
    Args:
        user: User object
        
    Returns:
        True if user is admin
    """
    # First check env variable (highest priority)
    if is_user_admin(user.id):
        return True
    
    # Then check database flag
    if hasattr(user, 'is_admin') and user.is_admin:
        return True
    
    return False


def get_admin_ids() -> list[int]:
    """Get list of admin user IDs"""
    return settings.admin_ids
