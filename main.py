"""
Main entry point for Expenses Bot
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config.settings import settings
from database.session import init_db, close_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Keep runtime logs lean in production to reduce I/O overhead.
if not settings.DEBUG and not settings.SQL_ECHO:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def _get_safe_miniapp_url() -> str | None:
    if not settings.MINIAPP_URL:
        return None
    return settings.MINIAPP_URL.rstrip('/') + '/'


async def configure_default_menu_button(bot: Bot) -> None:
    safe_miniapp_url = _get_safe_miniapp_url()
    if not safe_miniapp_url:
        logger.warning("MINIAPP_URL is empty, menu button was not configured")
        return

    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Open Mini App",
                web_app=WebAppInfo(url=safe_miniapp_url),
            )
        )
        logger.info("Default chat menu button configured for Mini App: %s", safe_miniapp_url)
    except Exception as exc:
        logger.warning("Failed to configure default chat menu button: %s", exc)


async def main():
    """Main function to run the bot"""
    
    logger.info("Starting Expenses Bot...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Register handlers
    from bot.handlers import admin, debt, expense, income, reports, start, stats, transfer
    from bot.handlers import settings as settings_handler
    dp.include_router(start.router)
    dp.include_router(income.router)
    dp.include_router(expense.router)
    dp.include_router(transfer.router)
    dp.include_router(stats.router)
    dp.include_router(debt.router)
    dp.include_router(reports.router)
    dp.include_router(settings_handler.router)
    dp.include_router(admin.router)
    
    logger.info("Handlers registered")

    try:
        await configure_default_menu_button(bot)
        # Start polling
        logger.info("Bot started successfully. Polling...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Error while running bot: {e}")
    finally:
        # Cleanup
        await bot.session.close()
        await close_db()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1)
