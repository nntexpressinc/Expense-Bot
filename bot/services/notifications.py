from __future__ import annotations

import logging

from aiogram import Bot
from sqlalchemy import select

from config.settings import settings
from config.admin import get_admin_ids
from database.models import Transaction, Transfer, User
from database.session import async_session_factory

logger = logging.getLogger(__name__)


async def _collect_admin_targets(exclude_user_id: int | None = None) -> list[tuple[int, str]]:
    targets: dict[int, str] = {admin_id: "uz" for admin_id in get_admin_ids()}

    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(User.id, User.language_code).where(
                    User.is_admin.is_(True),
                    User.is_active.is_(True),
                )
            )
        ).all()
        for admin_id, language_code in rows:
            targets[admin_id] = _normalize_lang(language_code)

    if exclude_user_id is not None:
        targets.pop(exclude_user_id, None)

    return sorted(targets.items(), key=lambda item: item[0])


def _build_transaction_caption(
    actor: User,
    transaction: Transaction,
    operation_key: str,
    category_name: str | None,
    lang: str,
) -> str:
    username = f"@{actor.username}" if actor.username else "-"
    category = category_name or "-"
    description = transaction.description or "-"
    operation_map = {
        "income": {"uz": "Daromad qo'shildi", "ru": "Добавлен доход", "en": "Income added"},
        "expense": {"uz": "Xarajat qo'shildi", "ru": "Добавлен расход", "en": "Expense added"},
    }
    operation_name = operation_map.get(operation_key, operation_map["expense"]).get(lang, operation_map["expense"]["en"])
    labels = {
        "uz": ("Foydalanuvchi", "Username", "Summa", "Kategoriya", "Izoh"),
        "ru": ("Пользователь", "Username", "Сумма", "Категория", "Комментарий"),
        "en": ("User", "Username", "Amount", "Category", "Description"),
    }
    user_label, username_label, amount_label, category_label, description_label = labels.get(lang, labels["en"])

    return (
        f"🔔 <b>{operation_name}</b>\n\n"
        f"👤 {user_label}: {actor.first_name} ({actor.id})\n"
        f"🔗 {username_label}: {username}\n"
        f"💰 {amount_label}: {transaction.amount} {transaction.currency}\n"
        f"📂 {category_label}: {category}\n"
        f"💬 {description_label}: {description}"
    )


async def notify_admins_about_transaction(
    bot: Bot,
    actor: User,
    transaction: Transaction,
    operation_key: str,
    category_name: str | None = None,
) -> None:
    admin_targets = await _collect_admin_targets(exclude_user_id=None)
    if not admin_targets:
        return

    for admin_id, lang in admin_targets:
        caption = _build_transaction_caption(
            actor=actor,
            transaction=transaction,
            operation_key=operation_key,
            category_name=category_name,
            lang=lang,
        )
        try:
            if transaction.attachment_file_id and transaction.attachment_type == "photo":
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=transaction.attachment_file_id,
                    caption=caption,
                    parse_mode="HTML",
                )
            elif transaction.attachment_file_id and transaction.attachment_type == "document":
                await bot.send_document(
                    chat_id=admin_id,
                    document=transaction.attachment_file_id,
                    caption=caption,
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=admin_id,
                    text=caption,
                    parse_mode="HTML",
                )
        except Exception as exc:  # pragma: no cover - network edge cases
            logger.warning("Failed to notify admin %s: %s", admin_id, exc)


def _normalize_lang(value: str | None) -> str:
    lang = (value or "uz").split("-")[0].lower()
    if lang in {"uz", "ru", "en"}:
        return lang
    return "uz"


def _user_display_name(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if full_name:
        return full_name
    return str(user.id)


def _format_transfer_text(
    *,
    lang: str,
    is_sender: bool,
    other_user: User,
    transfer: Transfer,
) -> str:
    other_name = _user_display_name(other_user)
    description = transfer.description or "-"

    if is_sender:
        text_map = {
            "uz": (
                "Transfer yuborildi.\n"
                f"Qabul qiluvchi: {other_name}\n"
                f"Summa: {transfer.amount} {transfer.currency}\n"
                f"Izoh: {description}"
            ),
            "ru": (
                "Перевод отправлен.\n"
                f"Получатель: {other_name}\n"
                f"Сумма: {transfer.amount} {transfer.currency}\n"
                f"Комментарий: {description}"
            ),
            "en": (
                "Transfer sent.\n"
                f"Recipient: {other_name}\n"
                f"Amount: {transfer.amount} {transfer.currency}\n"
                f"Comment: {description}"
            ),
        }
        return text_map.get(lang, text_map["en"])

    text_map = {
        "uz": (
            "Sizga transfer keldi.\n"
            f"Yuboruvchi: {other_name}\n"
            f"Summa: {transfer.amount} {transfer.currency}\n"
            f"Izoh: {description}"
        ),
        "ru": (
            "Вам поступил перевод.\n"
            f"Отправитель: {other_name}\n"
            f"Сумма: {transfer.amount} {transfer.currency}\n"
            f"Комментарий: {description}"
        ),
        "en": (
            "You received a transfer.\n"
            f"Sender: {other_name}\n"
            f"Amount: {transfer.amount} {transfer.currency}\n"
            f"Comment: {description}"
        ),
    }
    return text_map.get(lang, text_map["en"])


async def notify_transfer_participants(
    *,
    sender: User,
    recipient: User,
    transfer: Transfer,
    bot: Bot | None = None,
) -> None:
    if not settings.ENABLE_NOTIFICATIONS:
        return

    local_bot = bot
    owns_bot = False
    if local_bot is None:
        local_bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        owns_bot = True

    try:
        sender_text = _format_transfer_text(
            lang=_normalize_lang(sender.language_code),
            is_sender=True,
            other_user=recipient,
            transfer=transfer,
        )
        recipient_text = _format_transfer_text(
            lang=_normalize_lang(recipient.language_code),
            is_sender=False,
            other_user=sender,
            transfer=transfer,
        )

        for chat_id, text in (
            (sender.id, sender_text),
            (recipient.id, recipient_text),
        ):
            try:
                await local_bot.send_message(chat_id=chat_id, text=text)
            except Exception as exc:  # pragma: no cover - network edge cases
                logger.warning("Failed to notify transfer participant %s: %s", chat_id, exc)
    finally:
        if owns_bot:
            await local_bot.session.close()
