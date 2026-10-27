from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatMemberStatus, ChatType
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from database import Database
from translations import TEXT

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

LANGUAGES = {"fa", "en"}
PAGE_SIZE = 8
EVENT_RETENTION_DAYS = 90
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", str(PROJECT_DIR / "data" / "group_finder.sqlite3"))
ADMIN_ID_VALUE = os.getenv("ADMIN_ID", "").strip()
ADMIN_ID = (
    int(ADMIN_ID_VALUE)
    if ADMIN_ID_VALUE.isdigit() and int(ADMIN_ID_VALUE) > 0
    else None
)
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("group_finder")


def db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    return context.application.bot_data["database"]


def user_language(database: Database, user_id: int) -> str:
    return database.get_language(user_id) or "en"


def text(key: str, language: str, **values: object) -> str:
    return TEXT[key][language].format(**values)


async def require_private(update: Update, language: str) -> bool:
    if update.effective_chat and update.effective_chat.type == ChatType.PRIVATE:
        return True
    if update.effective_message:
        await update.effective_message.reply_text(text("private_only", language))
    return False


def menu_keyboard(language: str) -> ReplyKeyboardMarkup:
    labels = TEXT["menu"][language]
    return ReplyKeyboardMarkup(
        [
            [labels[0], labels[1]],
            [labels[2], labels[3]],
            [labels[4], labels[5]],
            [labels[6], labels[7]],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("فارسی", callback_data="language:fa"),
            InlineKeyboardButton("English", callback_data="language:en"),
        ]]
    )


def page_keyboard(callback_prefix: str, page: int, has_next: bool) -> InlineKeyboardMarkup | None:
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("‹", callback_data=f"{callback_prefix}:{page - 1}"))
    if has_next:
        buttons.append(InlineKeyboardButton("›", callback_data=f"{callback_prefix}:{page + 1}"))
    return InlineKeyboardMarkup([buttons]) if buttons else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = update.effective_user, update.effective_message
    if user is None or message is None:
        return
    referrer_id = None
    if context.args and context.args[0].startswith("ref_"):
        candidate = context.args[0][4:]
        if candidate.isdigit():
            referrer_id = int(candidate)
    database = db(context)
    database.ensure_user(user.id, referrer_id)
    language = database.get_language(user.id)
    if language is None:
        await message.reply_text(
            TEXT["choose_language"]["fa"] + "\n" + TEXT["choose_language"]["en"],
            reply_markup=language_keyboard(),
        )
        return
    await message.reply_text(text("welcome", language), reply_markup=menu_keyboard(language))


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.from_user is None or query.data is None:
        return
    language = query.data.partition(":")[2]
    if language not in LANGUAGES:
        await query.answer()
        return
    database = db(context)
    database.set_language(query.from_user.id, language)
    await query.answer()
    await query.edit_message_text(
        text("language_saved", language) + text("welcome", language)
    )
    if query.message:
        await query.message.reply_text(
            text("help_short", language), reply_markup=menu_keyboard(language)
        )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = update.effective_user, update.effective_message
    if message is None:
        return
    language = user_language(db(context), user.id) if user else "en"
    if not await require_private(update, language):
        return
    if user:
        db(context).ensure_user(user.id)
    await message.reply_text(
        text("language_prompt", language), reply_markup=language_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = update.effective_user, update.effective_message
    if message is None:
        return
    language = user_language(db(context), user.id) if user else "en"
    await message.reply_text(
        text("help", language), reply_markup=menu_keyboard(language)
    )


async def begin_search(
    update: Update, context: ContextTypes.DEFAULT_TYPE, language: str
) -> None:
    context.user_data["awaiting_search"] = True
    if update.effective_message:
        await update.effective_message.reply_text(text("search_prompt", language))


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return
    language = user_language(db(context), user.id)
    if await require_private(update, language):
        db(context).ensure_user(user.id)
        await begin_search(update, context, language)


async def search_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None or message.text is None:
        return
    language = user_language(db(context), user.id)
    value = message.text.strip()
    labels = TEXT["menu"][language]
    actions = {
        labels[0]: "search",
        labels[1]: "groups",
        labels[2]: "data",
        labels[3]: "delete",
        labels[4]: "subscription",
        labels[5]: "referral",
        labels[6]: "language",
        labels[7]: "help",
    }
    action = actions.get(value)
    if action == "search":
        await begin_search(update, context, language)
        return
    if action == "groups":
        if not db(context).consume_rate_limit(user.id, int(time.time())):
            await message.reply_text(text("rate_limited", language))
            return
        await show_groups(update, context, language, 0)
        return
    if action == "data":
        await show_my_data(update, context, language)
        return
    if action == "delete":
        await ask_delete(update, context, language)
        return
    if action == "subscription":
        await show_subscription(update, context, language)
        return
    if action == "referral":
        await show_referral(update, context, language)
        return
    if action == "language":
        await message.reply_text(
            text("language_prompt", language), reply_markup=language_keyboard()
        )
        return
    if action == "help":
        await message.reply_text(text("help", language), reply_markup=menu_keyboard(language))
        return

    if not context.user_data.get("awaiting_search"):
        await message.reply_text(text("unknown", language), reply_markup=menu_keyboard(language))
        return
    context.user_data.pop("awaiting_search", None)
    if value.isdecimal():
        if int(value) != user.id:
            await message.reply_text(text("search_other_id", language))
            return
        mode = "activity"
    else:
        mode = "groups"
        context.user_data["last_group_query"] = value
    database = db(context)
    if not database.consume_rate_limit(user.id, int(time.time())):
        await message.reply_text(text("rate_limited", language))
        return
    allowed, _, daily_limit = database.use_search(user.id)
    if not allowed:
        await message.reply_text(text("daily_limit", language, limit=daily_limit))
        return
    if mode == "activity":
        await show_activity_search(update, context, language, 0)
    else:
        await show_group_search(update, context, language, value, 0)


async def show_activity_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    language: str,
    page: int,
) -> None:
    user = update.effective_user
    if user is None:
        return
    rows = db(context).get_own_activity(user.id, page * PAGE_SIZE, PAGE_SIZE + 1)
    if not rows:
        output = text("search_not_found", language)
        markup = None
    else:
        output_lines = [text("activity_header", language)]
        for row in rows[:PAGE_SIZE]:
            output_lines.append(
                text(
                    "activity_line",
                    language,
                    title=row["title"],
                    count=row["event_count"],
                    first=row["first_seen"],
                    last=row["last_seen"],
                )
            )
        output_lines.append(text("activity_source_note", language))
        output_lines.append(
            "این رویدادها عضویت فعلی را اثبات نمی‌کنند."
            if language == "fa"
            else "These events do not prove current membership."
        )
        output = "\n\n".join(output_lines)
        markup = page_keyboard("activitypage", page, len(rows) > PAGE_SIZE)
    if update.effective_message:
        await update.effective_message.reply_text(output, reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(output, reply_markup=markup)


async def show_group_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    language: str,
    query: str,
    page: int,
) -> None:
    rows = db(context).search_groups(query, page * PAGE_SIZE, PAGE_SIZE + 1)
    if not rows:
        if update.effective_message:
            await update.effective_message.reply_text(text("search_not_found", language))
        elif update.callback_query:
            await update.callback_query.edit_message_text(text("search_not_found", language))
        return
    has_next = len(rows) > PAGE_SIZE
    lines = [text("search_results", language)]
    for row in rows[:PAGE_SIZE]:
        lines.append(
            text(
                "group_search_line",
                language,
                title=row["title"],
                kind=row["chat_type"],
                registered=row["created_at"],
                count=row["event_count"],
                first=row["first_event_at"] or "—",
                last=row["last_event_at"] or "—",
            )
        )
    markup = page_keyboard("searchpage", page, has_next)
    if update.effective_message:
        await update.effective_message.reply_text("\n".join(lines), reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("\n".join(lines), reply_markup=markup)


async def show_groups(
    update: Update, context: ContextTypes.DEFAULT_TYPE, language: str, page: int
) -> None:
    rows = db(context).list_groups(page * PAGE_SIZE, PAGE_SIZE + 1)
    if not rows:
        if update.effective_message:
            await update.effective_message.reply_text(text("groups_empty", language))
        elif update.callback_query:
            await update.callback_query.edit_message_text(text("groups_empty", language))
        return
    lines = [text("groups_header", language)]
    for row in rows[:PAGE_SIZE]:
        lines.append(
            text(
                "group_line",
                language,
                title=row["title"],
                count=row["opted_in_users"],
                events=row["event_count"],
                registered=row["created_at"],
                last=row["last_event_at"] or "—",
            )
        )
    markup = page_keyboard("groups", page, len(rows) > PAGE_SIZE)
    if update.effective_message:
        await update.effective_message.reply_text("\n".join(lines), reply_markup=markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("\n".join(lines), reply_markup=markup)


async def show_my_data(
    update: Update, context: ContextTypes.DEFAULT_TYPE, language: str
) -> None:
    user, message = update.effective_user, update.effective_message
    if user is None or message is None:
        return
    if not await require_private(update, language):
        return
    db(context).ensure_user(user.id)
    data = db(context).user_data(user.id)
    if not data:
        await message.reply_text(text("search_not_found", language))
        return
    selected_language = data["user"]["language"] or "—"
    summary = text(
        "data_summary",
        language,
        language=selected_language,
        consents=data["consent_count"],
        events=data["event_count"],
        referrals=data["referral_count"],
    )
    activity = data["activity"]
    lines = [text("data_header", language), summary]
    if activity:
        lines.append(text("activity_header", language))
        for row in activity[:PAGE_SIZE]:
            lines.append(
                text(
                    "activity_line",
                    language,
                    title=row["title"],
                    count=row["event_count"],
                    first=row["first_seen"],
                    last=row["last_seen"],
                )
            )
    else:
        lines.append(text("no_activity", language))

    orders = db(context).order_history(user.id)
    if orders:
        lines.append(text("orders_header", language))
        for order in orders:
            lines.append(
                text(
                    "order_line",
                    language,
                    plan=order[f"title_{language}"],
                    amount=order["amount"],
                    currency=text("stars_currency", language),
                    status=TEXT["order_status"][language].get(
                        order["status"], order["status"]
                    ),
                    order_id=order["order_id"],
                    created=order["created_at"],
                    paid=order["paid_at"] or text("not_paid", language),
                )
            )
    subscription = data["subscription"]
    if subscription:
        lines.append(
            text(
                "subscription_current",
                language,
                plan=subscription[f"title_{language}"],
                expires=subscription["expires_at"],
                limit=subscription["searches_per_day"],
            )
        )
    upcoming = data["next_subscription"]
    if upcoming:
        lines.append(
            text(
                "subscription_scheduled",
                language,
                plan=upcoming[f"title_{language}"],
                starts=upcoming["started_at"],
                expires=upcoming["expires_at"],
                limit=upcoming["searches_per_day"],
            )
        )
    await message.reply_text("\n\n".join(lines), reply_markup=menu_keyboard(language))


async def ask_delete(update: Update, context: ContextTypes.DEFAULT_TYPE, language: str) -> None:
    if update.effective_message:
        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton(
                    "حذف" if language == "fa" else "Delete",
                    callback_data="delete:confirm",
                ),
                InlineKeyboardButton(
                    "لغو" if language == "fa" else "Cancel",
                    callback_data="delete:cancel",
                ),
            ]]
        )
        await update.effective_message.reply_text(
            text("delete_confirm", language), reply_markup=keyboard
        )


async def show_subscription(
    update: Update, context: ContextTypes.DEFAULT_TYPE, language: str
) -> None:
    user = update.effective_user
    if user is None:
        return
    if not await require_private(update, language):
        return
    database = db(context)
    database.ensure_user(user.id)
    current = database.get_subscription(user.id)
    limit = database.get_search_limit(user.id)
    if update.effective_message:
        lines = [text("subscription_header", language)]
        if current:
            lines.append(
                text(
                    "subscription_current",
                    language,
                    plan=current[f"title_{language}"],
                    expires=current["expires_at"],
                    limit=current["searches_per_day"],
                )
            )
        else:
            lines.append(text("subscription_free", language, limit=limit))
        upcoming = database.get_next_subscription(user.id)
        if upcoming:
            lines.append(
                text(
                    "subscription_scheduled",
                    language,
                    plan=upcoming[f"title_{language}"],
                    starts=upcoming["started_at"],
                    expires=upcoming["expires_at"],
                    limit=upcoming["searches_per_day"],
                )
            )
        plans = database.list_plans()
        buttons = []
        for plan in plans:
            if plan["slug"] == "free":
                continue
            buttons.append(
                InlineKeyboardButton(
                    plan[f"title_{language}"],
                    callback_data=f"plan:{plan['slug']}",
                )
            )
            lines.append(
                text(
                    "plan_line",
                    language,
                    plan=plan[f"title_{language}"],
                    price=plan["price_stars"],
                    days=plan["duration_days"],
                    limit=plan["searches_per_day"],
                    features=text("plan_features", language),
                )
            )
        keyboard = [
            buttons[index : index + 2] for index in range(0, len(buttons), 2)
        ]
        await update.effective_message.reply_text(
            "\n\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else menu_keyboard(language),
        )


async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE, language: str) -> None:
    user = update.effective_user
    if user is None or update.effective_message is None:
        return
    if not await require_private(update, language):
        return
    db(context).ensure_user(user.id)
    me = await context.bot.get_me()
    count, referrals = db(context).referral_stats(user.id)
    link = f"https://t.me/{me.username}?start=ref_{user.id}"
    output = [text("referral", language, link=link, count=count)]
    if referrals:
        output.append(text("referral_history", language))
        output.extend(
            text(
                "referral_line",
                language,
                user_id=row["referred_id"],
                created=row["created_at"],
            )
            for row in referrals
        )
    else:
        output.append(text("referral_empty", language))
    await update.effective_message.reply_text(
        "\n\n".join(output),
        reply_markup=menu_keyboard(language),
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or query.data is None:
        return
    database = db(context)
    language = user_language(database, user.id)
    data = query.data
    if data.startswith("language:"):
        await choose_language(update, context)
        return
    if data.startswith("delete:"):
        if not update.effective_chat or update.effective_chat.type != ChatType.PRIVATE:
            await query.answer(text("private_only", language), show_alert=True)
            return
        if data == "delete:confirm":
            database.delete_user_data(user.id)
            context.user_data.clear()
            await query.answer()
            await query.edit_message_text(text("delete_done", language))
        else:
            await query.answer()
            await query.edit_message_text(text("delete_cancelled", language))
        return
    if data.startswith("groups:"):
        if not database.consume_rate_limit(user.id, int(time.time())):
            await query.answer(text("rate_limited", language), show_alert=True)
            return
        await query.answer()
        await show_groups(update, context, language, int(data.split(":")[1]))
        return
    if data.startswith("searchpage:"):
        if not database.consume_rate_limit(user.id, int(time.time())):
            await query.answer(text("rate_limited", language), show_alert=True)
            return
        await query.answer()
        search_query = context.user_data.get("last_group_query")
        if not search_query:
            await query.edit_message_text(text("search_prompt", language))
            return
        await show_group_search(
            update, context, language, search_query, int(data.split(":")[1])
        )
        return
    if data.startswith("activitypage:"):
        if not database.consume_rate_limit(user.id, int(time.time())):
            await query.answer(text("rate_limited", language), show_alert=True)
            return
        await query.answer()
        await show_activity_search(update, context, language, int(data.split(":")[1]))
        return
    if data.startswith("plan:"):
        if not update.effective_chat or update.effective_chat.type != ChatType.PRIVATE:
            await query.answer(text("private_only", language), show_alert=True)
            return
        if not database.consume_rate_limit(user.id, int(time.time())):
            await query.answer(text("rate_limited", language), show_alert=True)
            return
        slug = data.split(":", 1)[1]
        if slug == "trial":
            trial = database.get_plan("trial")
            if trial is None or not trial["active"]:
                await query.answer(text("plan_unavailable", language), show_alert=True)
                return
            claimed = database.claim_trial(user.id)
            await query.answer()
            await query.edit_message_text(
                text("trial_claimed" if claimed else "trial_already_claimed", language)
            )
            return
        try:
            order = database.create_order(user.id, slug)
        except ValueError:
            await query.answer(text("plan_unavailable", language), show_alert=True)
            return
        await query.answer()
        if query.message is None:
            return
        await query.message.reply_text(
            text(
                "order_created",
                language,
                order_id=order["order_id"],
                amount=order["amount"],
            )
        )
        await query.message.reply_invoice(
            title=order[f"title_{language}"],
            description=text("invoice_description", language),
            payload=order["order_id"],
            currency="XTR",
            prices=[LabeledPrice(order[f"title_{language}"], order["amount"])],
            provider_token="",
        )
        return
    await query.answer()


async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query is None:
        return
    order = db(context).get_pending_order(query.invoice_payload, query.from_user.id)
    valid = bool(
        order
        and query.currency == order["currency"] == "XTR"
        and query.total_amount == order["amount"]
    )
    language = user_language(db(context), query.from_user.id)
    await query.answer(
        ok=valid,
        error_message=None if valid else text("payment_invalid", language),
    )


async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = update.effective_user, update.effective_message
    if user is None or message is None or message.successful_payment is None:
        return
    payment = message.successful_payment
    database = db(context)
    succeeded = database.mark_order_paid(
        payment.invoice_payload,
        user.id,
        payment.currency,
        payment.total_amount,
        payment.telegram_payment_charge_id,
    )
    language = user_language(database, user.id)
    if not succeeded:
        logger.warning(
            "Rejected duplicate or mismatched Telegram Stars payment"
        )
        message_key = (
            "payment_duplicate"
            if database.charge_was_processed(payment.telegram_payment_charge_id)
            else "payment_invalid"
        )
        await message.reply_text(text(message_key, language))
        return
    await message.reply_text(
        text("payment_success", language, order_id=payment.invoice_payload)
    )
    if ADMIN_ID:
        admin_language = user_language(database, ADMIN_ID)
        await context.bot.send_message(
            ADMIN_ID,
            text(
                "payment_admin",
                admin_language,
                order_id=payment.invoice_payload,
                amount=payment.total_amount,
                charge_id=payment.telegram_payment_charge_id,
            ),
        )


async def consent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat, user, message = update.effective_chat, update.effective_user, update.effective_message
    if chat is None or user is None or message is None:
        return
    language = user_language(db(context), user.id)
    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        await message.reply_text(text("private_only", language))
        return
    database = db(context)
    group = database.get_group(chat.id)
    if group is None or not group["enabled"]:
        await message.reply_text(text("tracking_not_enabled", language))
        return
    database.ensure_user(user.id)
    database.consent(user.id, chat.id)
    await message.reply_text(text("consent_saved", language))


async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat, user, message = update.effective_chat, update.effective_user, update.effective_message
    if chat is None or user is None or message is None:
        return
    language = user_language(db(context), user.id)
    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        await message.reply_text(text("private_only", language))
        return
    db(context).revoke_consent(user.id, chat.id)
    await message.reply_text(text("consent_revoked", language))


async def is_group_admin(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool | None:
    chat, user = update.effective_chat, update.effective_user
    if chat is None or user is None:
        return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
    except TelegramError:
        logger.exception("Could not verify group admin for chat_id=%s", chat.id)
        return None
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}


async def enable_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat, message = update.effective_chat, update.effective_message
    user = update.effective_user
    if chat is None or message is None or user is None:
        return
    language = user_language(db(context), user.id)
    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        await message.reply_text(text("private_only", language))
        return
    admin = await is_group_admin(update, context)
    if admin is None:
        await message.reply_text(text("admin_check_failed", language))
        return
    if not admin:
        await message.reply_text(text("admin_required", language))
        return
    database = db(context)
    database.upsert_group(chat.id, chat.title or str(chat.id), chat.type)
    database.set_group_enabled(chat.id, True)
    await message.reply_text(text("tracking_enabled", language))


async def disable_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat, message, user = update.effective_chat, update.effective_message, update.effective_user
    if chat is None or message is None or user is None:
        return
    language = user_language(db(context), user.id)
    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        await message.reply_text(text("private_only", language))
        return
    admin = await is_group_admin(update, context)
    if admin is None:
        await message.reply_text(text("admin_check_failed", language))
        return
    if not admin:
        await message.reply_text(text("admin_required", language))
        return
    db(context).delete_group(chat.id)
    await message.reply_text(text("tracking_disabled", language))


async def track_group_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat, message, user = update.effective_chat, update.effective_message, update.effective_user
    if (
        chat is None
        or message is None
        or user is None
        or user.is_bot
        or chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP}
    ):
        return
    occurred_at = message.date or datetime.now(timezone.utc)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    else:
        occurred_at = occurred_at.astimezone(timezone.utc)
    database = db(context)
    if not database.has_consent(user.id, chat.id):
        return
    database.record_group_event(
        chat.id,
        chat.title or str(chat.id),
        chat.type,
        user.id,
        message.message_id,
        occurred_at,
    )


async def chat_membership_changed(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    change = update.my_chat_member
    if change is None:
        return
    chat = change.chat
    if chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL}:
        return
    new_status = change.new_chat_member.status
    if new_status in {ChatMemberStatus.LEFT, ChatMemberStatus.BANNED}:
        db(context).delete_group(chat.id)
    elif new_status in {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
    }:
        db(context).upsert_group(
            chat.id,
            chat.title or str(chat.id),
            chat.type,
            catalogued=chat.type == ChatType.CHANNEL,
        )


async def data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        language = user_language(db(context), user.id)
        if await require_private(update, language):
            await show_my_data(update, context, language)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        language = user_language(db(context), user.id)
        if await require_private(update, language):
            await ask_delete(update, context, language)


async def subscription_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if user:
        language = user_language(db(context), user.id)
        if await require_private(update, language):
            await show_subscription(update, context, language)


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        language = user_language(db(context), user.id)
        if await require_private(update, language):
            await show_referral(update, context, language)


async def paysupport_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user, message = update.effective_user, update.effective_message
    if message is None:
        return
    language = user_language(db(context), user.id) if user else "en"
    if not await require_private(update, language):
        return
    if not SUPPORT_USERNAME:
        await message.reply_text(text("support_missing", language))
        return
    await message.reply_text(
        text("payment_support", language, contact=f"@{SUPPORT_USERNAME}")
    )


async def admin_set_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = update.effective_user, update.effective_message
    language = user_language(db(context), user.id) if user else "en"
    if ADMIN_ID is None or user is None or user.id != ADMIN_ID:
        if message:
            await message.reply_text(text("admin_only", language))
        return
    if len(context.args) not in {4, 5}:
        await message.reply_text(text("plan_config_usage", language))
        return
    slug = context.args[0].lower()
    try:
        price, days, searches = (int(value) for value in context.args[1:])
        title_fa, title_en = None, None
        if len(context.args) == 5:
            names = context.args[4].split("|", 1)
            if len(names) != 2:
                raise ValueError("plan names must be separated by |")
            title_fa, title_en = names
        db(context).configure_plan(
            slug, price, days, searches, title_fa=title_fa, title_en=title_en
        )
    except (ValueError, TypeError):
        await message.reply_text(text("plan_config_usage", language))
        return
    await message.reply_text(text("plan_config_done", language))


async def admin_disable_plan(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user, message = update.effective_user, update.effective_message
    language = user_language(db(context), user.id) if user else "en"
    if ADMIN_ID is None or user is None or user.id != ADMIN_ID:
        if message:
            await message.reply_text(text("admin_only", language))
        return
    if message is None or len(context.args) != 1:
        if message:
            await message.reply_text(text("plan_disable_usage", language))
        return
    try:
        db(context).disable_plan(context.args[0].lower())
    except ValueError:
        await message.reply_text(text("plan_disable_usage", language))
        return
    await message.reply_text(text("plan_config_done", language))


async def startup(application: Application) -> None:
    database: Database = application.bot_data["database"]
    removed = database.prune_old_events(EVENT_RETENTION_DAYS)
    if removed:
        logger.info("Pruned %s expired activity events", removed)
    logger.info("Group Finder started; database=%s", DB_PATH)


async def shutdown(application: Application) -> None:
    database = application.bot_data.get("database")
    if database:
        database.close()


def build_application(token: str, database: Database) -> Application:
    application = (
        Application.builder()
        .token(token)
        .post_init(startup)
        .post_shutdown(shutdown)
        .build()
    )
    application.bot_data["database"] = database

    for command, handler in [
        ("start", start),
        ("help", help_command),
        ("language", language_command),
        ("search", search_command),
        ("data", data_command),
        ("delete_my_data", delete_command),
        ("subscription", subscription_command),
        ("status", subscription_command),
        ("buy", subscription_command),
        ("referral", referral_command),
        ("paysupport", paysupport_command),
        ("consent", consent_command),
        ("revoke", revoke_command),
        ("enable_tracking", enable_tracking),
        ("disable_tracking", disable_tracking),
        ("setplan", admin_set_plan),
        ("disableplan", admin_disable_plan),
    ]:
        application.add_handler(CommandHandler(command, handler))

    application.add_handler(PreCheckoutQueryHandler(precheckout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, paid))
    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
            pattern=r"^(language:|delete:|groups:|searchpage:|activitypage:|plan:)",
        )
    )
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
            track_group_activity,
        )
    )
    application.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, search_text)
    )
    application.add_handler(
        ChatMemberHandler(
            chat_membership_changed, ChatMemberHandler.MY_CHAT_MEMBER
        )
    )
    return application


def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise SystemExit(
            "BOT_TOKEN is missing. Set it in the local .env file; "
            "never share it in chat or commit it."
        )
    if ADMIN_ID_VALUE and ADMIN_ID is None:
        raise SystemExit("ADMIN_ID must be a positive numeric Telegram user ID")
    database = Database(DB_PATH)
    application = build_application(BOT_TOKEN, database)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
