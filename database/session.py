"""
Database configuration and session management
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for all models
Base = declarative_base()


async def get_session() -> AsyncSession:
    """
    Dependency for getting database session
    
    Usage:
        async with get_session() as session:
            # Your database operations
            pass
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


# Alias for FastAPI dependency
async def get_db() -> AsyncSession:
    """
    FastAPI dependency for getting database session
    
    Usage in FastAPI:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # Your database operations
            pass
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables)"""
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered
        from database import models
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Extend enums for new transaction types (idempotent).
        await conn.execute(text("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'debt'"))
        await conn.execute(text("ALTER TYPE transaction_type ADD VALUE IF NOT EXISTS 'debt_payment'"))

        # Lightweight runtime migration for old databases.
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS transactions
                ADD COLUMN IF NOT EXISTS attachment_file_id VARCHAR(512),
                ADD COLUMN IF NOT EXISTS attachment_type VARCHAR(20),
                ADD COLUMN IF NOT EXISTS attachment_name VARCHAR(255)
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS group_id BIGINT
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE users
                SET group_id = id
                WHERE group_id IS NULL
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS users
                ADD COLUMN IF NOT EXISTS active_group_id BIGINT,
                ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(20) DEFAULT 'light'
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_users_group_id ON users(group_id)
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_active_group_id ON users(active_group_id)"))

        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS transactions
                ADD COLUMN IF NOT EXISTS group_id BIGINT,
                ADD COLUMN IF NOT EXISTS funding_source VARCHAR(20) DEFAULT 'main'
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_group_id ON transactions(group_id)"))

        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS transfers
                ADD COLUMN IF NOT EXISTS group_id BIGINT
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transfers_group_id ON transfers(group_id)"))

        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS transfer_expenses
                ADD COLUMN IF NOT EXISTS group_id BIGINT
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transfer_expenses_group_id ON transfer_expenses(group_id)"))

        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS debts
                ADD COLUMN IF NOT EXISTS group_id BIGINT,
                ADD COLUMN IF NOT EXISTS used_amount NUMERIC(15,2) DEFAULT 0,
                ADD COLUMN IF NOT EXISTS source_name VARCHAR(255),
                ADD COLUMN IF NOT EXISTS source_contact VARCHAR(255),
                ADD COLUMN IF NOT EXISTS reference VARCHAR(255),
                ADD COLUMN IF NOT EXISTS note TEXT,
                ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'active',
                ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_debts_group_id ON debts(group_id)"))

        # Populate groups from legacy users.group_id values.
        await conn.execute(
            text(
                """
                INSERT INTO groups (id, name, created_by, is_active, created_at, updated_at)
                SELECT DISTINCT
                    COALESCE(u.group_id, u.id) AS group_id,
                    (
                        COALESCE(
                            NULLIF(TRIM(CONCAT(COALESCE(u.first_name, ''), ' ', COALESCE(u.last_name, ''))), ''),
                            NULLIF(u.username, ''),
                            'Group ' || COALESCE(u.group_id, u.id)::text
                        ) || ' Team'
                    ) AS name,
                    u.id,
                    TRUE,
                    NOW(),
                    NOW()
                FROM users u
                WHERE COALESCE(u.group_id, u.id) IS NOT NULL
                ON CONFLICT (id) DO NOTHING
                """
            )
        )

        await conn.execute(
            text(
                """
                INSERT INTO user_groups (user_id, group_id, role, joined_at)
                SELECT
                    u.id,
                    COALESCE(u.group_id, u.id),
                    CASE
                        WHEN u.is_admin = TRUE OR COALESCE(u.group_id, u.id) = u.id THEN 'admin'
                        ELSE 'member'
                    END,
                    NOW()
                FROM users u
                WHERE COALESCE(u.group_id, u.id) IS NOT NULL
                ON CONFLICT (user_id, group_id) DO NOTHING
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE users
                SET active_group_id = COALESCE(active_group_id, group_id, id),
                    theme_preference = COALESCE(theme_preference, 'light')
                WHERE active_group_id IS NULL OR theme_preference IS NULL
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE transactions t
                SET group_id = COALESCE(t.group_id, u.active_group_id, u.group_id, u.id),
                    funding_source = COALESCE(NULLIF(t.funding_source, ''), 'main')
                FROM users u
                WHERE t.user_id = u.id
                  AND (t.group_id IS NULL OR t.funding_source IS NULL)
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE transfers tr
                SET group_id = COALESCE(tr.group_id, u.active_group_id, u.group_id, u.id)
                FROM users u
                WHERE tr.sender_id = u.id
                  AND tr.group_id IS NULL
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE transfer_expenses te
                SET group_id = tr.group_id
                FROM transfers tr
                WHERE te.transfer_id = tr.id
                  AND te.group_id IS NULL
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE debts d
                SET group_id = COALESCE(d.group_id, u.active_group_id, u.group_id, u.id),
                    used_amount = COALESCE(d.used_amount, 0),
                    status = CASE
                        WHEN d.archived_at IS NOT NULL THEN 'archived'
                        WHEN d.remaining_amount <= 0 THEN 'fully_repaid'
                        WHEN d.remaining_amount < d.amount THEN 'partially_repaid'
                        ELSE COALESCE(NULLIF(d.status, ''), 'active')
                    END
                FROM users u
                WHERE d.user_id = u.id
                  AND (d.group_id IS NULL OR d.status IS NULL OR d.used_amount IS NULL)
                """
            )
        )

        # Seed core system categories for both bot and mini app flows.
        system_categories = [
            ("Salary", "income", "💼"),
            ("Sales", "income", "🛒"),
            ("Transfer In", "income", "📥"),
            ("Other income", "income", "➕"),
            ("Food", "expense", "🍽"),
            ("Transport", "expense", "🚚"),
            ("Materials", "expense", "📦"),
            ("Debt repayment", "expense", "💳"),
            ("Other expense", "expense", "➖"),
        ]
        for name, cat_type, icon in system_categories:
            await conn.execute(
                text(
                    """
                    INSERT INTO categories (name, type, icon, is_system)
                    SELECT
                        CAST(:name AS VARCHAR(255)),
                        CAST(:cat_type AS category_type),
                        CAST(:icon AS VARCHAR(32)),
                        TRUE
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM categories
                        WHERE name = CAST(:name AS VARCHAR(255))
                          AND type = CAST(:cat_type AS category_type)
                          AND is_system = TRUE
                          AND user_id IS NULL
                    )
                    """
                ),
                {"name": name, "cat_type": cat_type, "icon": icon},
            )

        logger.info("Database initialized successfully")


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")
