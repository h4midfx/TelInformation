from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._migrate_legacy_users()
        self._create_schema()

    def _migrate_legacy_users(self) -> None:
        columns = self.connection.execute("PRAGMA table_info(users)").fetchall()
        language_column = next(
            (column for column in columns if column["name"] == "language"), None
        )
        if language_column is None or not language_column["notnull"]:
            return
        with self.connection:
            self.connection.execute("ALTER TABLE users RENAME TO users_legacy_v1")
            self.connection.execute(
                """
                CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT CHECK (language IS NULL OR language IN ('fa', 'en')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self.connection.execute(
                """
                INSERT INTO users(user_id, language, created_at, updated_at)
                SELECT user_id, language, created_at, updated_at FROM users_legacy_v1
                """
            )
            self.connection.execute("DROP TABLE users_legacy_v1")

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT CHECK (language IS NULL OR language IN ('fa', 'en')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS referrals (
                referred_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                referrer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                CHECK (referred_id != referrer_id)
            );
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                chat_type TEXT NOT NULL CHECK (chat_type IN ('group', 'supergroup', 'channel')),
                enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
                catalogued INTEGER NOT NULL DEFAULT 0 CHECK (catalogued IN (0, 1)),
                created_at TEXT NOT NULL,
                last_event_at TEXT
            );
            CREATE TABLE IF NOT EXISTS consents (
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                chat_id INTEGER NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
                consented_at TEXT NOT NULL,
                PRIMARY KEY (user_id, chat_id)
            );
            CREATE TABLE IF NOT EXISTS group_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                UNIQUE (chat_id, message_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS group_events_user_idx
                ON group_events(user_id, occurred_at);
            CREATE INDEX IF NOT EXISTS group_events_chat_idx
                ON group_events(chat_id, occurred_at);
            CREATE TABLE IF NOT EXISTS plans (
                slug TEXT PRIMARY KEY,
                title_fa TEXT NOT NULL,
                title_en TEXT NOT NULL,
                currency TEXT NOT NULL DEFAULT 'XTR' CHECK (currency = 'XTR'),
                price_stars INTEGER NOT NULL DEFAULT 0 CHECK (price_stars >= 0),
                duration_days INTEGER NOT NULL CHECK (duration_days >= 0),
                searches_per_day INTEGER NOT NULL CHECK (searches_per_day > 0),
                features_json TEXT NOT NULL DEFAULT '["group_search","own_activity_search"]',
                active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
                is_trial INTEGER NOT NULL DEFAULT 0 CHECK (is_trial IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS trial_claims (
                user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                claimed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                plan_slug TEXT NOT NULL REFERENCES plans(slug),
                title_fa TEXT NOT NULL,
                title_en TEXT NOT NULL,
                searches_per_day INTEGER NOT NULL,
                features_json TEXT NOT NULL,
                started_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                plan_slug TEXT NOT NULL REFERENCES plans(slug),
                title_fa TEXT NOT NULL,
                title_en TEXT NOT NULL,
                amount INTEGER NOT NULL CHECK (amount >= 0),
                currency TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                searches_per_day INTEGER NOT NULL,
                features_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'cancelled')),
                created_at TEXT NOT NULL,
                paid_at TEXT,
                charge_id TEXT UNIQUE
            );
            CREATE INDEX IF NOT EXISTS orders_user_idx ON orders(user_id, created_at);
            CREATE TABLE IF NOT EXISTS search_usage (
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                usage_date TEXT NOT NULL,
                searches INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            );
            CREATE TABLE IF NOT EXISTS rate_limits (
                user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                window_started INTEGER NOT NULL,
                request_count INTEGER NOT NULL
            );
            """
        )
        self.connection.executemany(
            """
            INSERT OR IGNORE INTO plans
                (slug, title_fa, title_en, price_stars, duration_days,
                 searches_per_day, active, is_trial)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("free", "رایگان", "Free", 0, 0, 5, 1, 0),
                ("trial", "آزمایشی", "Trial", 0, 7, 20, 1, 1),
                ("weekly", "هفتگی", "Weekly", 0, 7, 30, 0, 0),
                ("monthly", "ماهانه", "Monthly", 0, 30, 100, 0, 0),
                ("premium", "ویژه", "Premium", 0, 30, 500, 0, 0),
            ],
        )
        self.connection.commit()

    def ensure_user(self, user_id: int, referrer_id: int | None = None) -> None:
        now = timestamp()
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO users(user_id, language, created_at, updated_at) "
                "VALUES (?, NULL, ?, ?)",
                (user_id, now, now),
            )
            if referrer_id and referrer_id != user_id:
                exists = self.connection.execute(
                    "SELECT 1 FROM referrals WHERE referred_id = ?", (user_id,)
                ).fetchone()
                if exists is None and self.connection.execute(
                    "SELECT 1 FROM users WHERE user_id = ?", (referrer_id,)
                ).fetchone():
                    self.connection.execute(
                        "INSERT INTO referrals(referred_id, referrer_id, created_at) "
                        "VALUES (?, ?, ?)",
                        (user_id, referrer_id, now),
                    )

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

    def get_language(self, user_id: int) -> str | None:
        row = self.connection.execute(
            "SELECT language FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["language"] if row else None

    def set_language(self, user_id: int, language: str) -> None:
        if language not in {"fa", "en"}:
            raise ValueError("language must be 'fa' or 'en'")
        self.ensure_user(user_id)
        with self.connection:
            self.connection.execute(
                "UPDATE users SET language = ?, updated_at = ? WHERE user_id = ?",
                (language, timestamp(), user_id),
            )

    def upsert_group(
        self, chat_id: int, title: str, chat_type: str, catalogued: bool = False
    ) -> None:
        if chat_type not in {"group", "supergroup", "channel"}:
            raise ValueError("only groups, supergroups, and channels can be registered")
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO groups(chat_id, title, chat_type, catalogued, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title,
                    chat_type=excluded.chat_type,
                    catalogued=MAX(groups.catalogued, excluded.catalogued)
                """,
                (chat_id, title or str(chat_id), chat_type, int(catalogued), timestamp()),
            )

    def set_group_enabled(self, chat_id: int, enabled: bool) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE groups SET enabled = ? WHERE chat_id = ?",
                (int(enabled), chat_id),
            )
            if enabled:
                self.connection.execute(
                    "UPDATE groups SET catalogued=1 WHERE chat_id=?", (chat_id,)
                )

    def get_group(self, chat_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM groups WHERE chat_id = ?", (chat_id,)
        ).fetchone()

    def list_groups(self, offset: int = 0, page_size: int = 8) -> list[sqlite3.Row]:
        return self.connection.execute(
            """
            SELECT g.chat_id, g.title, g.chat_type, g.created_at,
                   MIN(e.occurred_at) AS first_event_at,
                   MAX(e.occurred_at) AS last_event_at,
                   COUNT(e.event_id) AS event_count,
                   COUNT(DISTINCT e.user_id) AS opted_in_users
            FROM groups g LEFT JOIN group_events e ON e.chat_id = g.chat_id
            WHERE g.catalogued = 1
            GROUP BY g.chat_id
            ORDER BY g.title COLLATE NOCASE
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()

    def delete_group(self, chat_id: int) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM groups WHERE chat_id = ?", (chat_id,))

    def consent(self, user_id: int, chat_id: int) -> bool:
        now = timestamp()
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO consents(user_id, chat_id, consented_at) "
                "VALUES (?, ?, ?)",
                (user_id, chat_id, now),
            )
        return self.has_consent(user_id, chat_id)

    def has_consent(self, user_id: int, chat_id: int) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM consents WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        ).fetchone() is not None

    def revoke_consent(self, user_id: int, chat_id: int) -> None:
        with self.connection:
            self.connection.execute(
                "DELETE FROM group_events WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id),
            )
            self.connection.execute(
                "DELETE FROM consents WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id),
            )

    def record_group_event(
        self,
        chat_id: int,
        title: str,
        chat_type: str,
        user_id: int,
        message_id: int,
        occurred_at: datetime,
    ) -> bool:
        consent = self.connection.execute(
            "SELECT consented_at FROM consents WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        ).fetchone()
        if consent is None or timestamp(occurred_at) < consent["consented_at"]:
            return False
        now = timestamp(occurred_at)
        self.upsert_group(chat_id, title, chat_type)
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO group_events
                    (chat_id, user_id, event_type, occurred_at, message_id)
                SELECT ?, ?, 'message_activity', ?, ?
                WHERE EXISTS (
                    SELECT 1 FROM groups WHERE chat_id = ? AND enabled = 1
                )
                """,
                (chat_id, user_id, now, message_id, chat_id),
            )
            if cursor.rowcount:
                self.connection.execute(
                    "UPDATE groups SET last_event_at = ? WHERE chat_id = ?",
                    (now, chat_id),
                )
            return cursor.rowcount == 1

    def get_own_activity(
        self, user_id: int, offset: int = 0, page_size: int | None = None
    ) -> list[sqlite3.Row]:
        limit_sql = "LIMIT ? OFFSET ?" if page_size is not None else ""
        parameters: tuple[Any, ...] = (user_id, page_size, offset) if page_size is not None else (user_id,)
        return self.connection.execute(
            f"""
            SELECT g.chat_id, g.title,
                   MIN(e.occurred_at) AS first_seen,
                   MAX(e.occurred_at) AS last_seen,
                   COUNT(e.event_id) AS event_count
            FROM group_events e JOIN groups g ON g.chat_id = e.chat_id
            WHERE e.user_id = ? AND g.enabled = 1
            GROUP BY g.chat_id ORDER BY last_seen DESC
            {limit_sql}
            """,
            parameters,
        ).fetchall()

    def search_groups(self, query: str, offset: int = 0, page_size: int = 8) -> list[sqlite3.Row]:
        return self.connection.execute(
            """
            SELECT g.title, g.chat_type, g.created_at,
                   MIN(e.occurred_at) AS first_event_at,
                   MAX(e.occurred_at) AS last_event_at,
                   COUNT(e.event_id) AS event_count
            FROM groups g LEFT JOIN group_events e ON e.chat_id = g.chat_id
            WHERE g.catalogued = 1 AND g.title LIKE ? ESCAPE '\\'
            GROUP BY g.chat_id
            ORDER BY g.title COLLATE NOCASE LIMIT ? OFFSET ?
            """,
            (f"%{self._escape_like(query)}%", page_size, offset),
        ).fetchall()

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def consume_rate_limit(self, user_id: int, now_epoch: int, limit: int = 5) -> bool:
        window_seconds = 60
        self.ensure_user(user_id)
        with self.connection:
            row = self.connection.execute(
                "SELECT window_started, request_count FROM rate_limits WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None or now_epoch - row["window_started"] >= window_seconds:
                self.connection.execute(
                    """
                    INSERT INTO rate_limits(user_id, window_started, request_count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id) DO UPDATE SET
                        window_started=excluded.window_started, request_count=1
                    """,
                    (user_id, now_epoch),
                )
                return True
            if row["request_count"] >= limit:
                return False
            self.connection.execute(
                "UPDATE rate_limits SET request_count=request_count+1 WHERE user_id=?",
                (user_id,),
            )
            return True

    def get_plan(self, slug: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM plans WHERE slug = ?", (slug,)
        ).fetchone()

    def list_plans(self, include_inactive: bool = False) -> list[sqlite3.Row]:
        where = "" if include_inactive else "WHERE active = 1"
        return self.connection.execute(
            f"SELECT * FROM plans {where} ORDER BY "
            "CASE slug WHEN 'free' THEN 0 WHEN 'trial' THEN 1 ELSE 2 END, slug"
        ).fetchall()

    def configure_plan(
        self,
        slug: str,
        price_stars: int,
        duration_days: int,
        searches_per_day: int,
        title_fa: str | None = None,
        title_en: str | None = None,
    ) -> None:
        if slug not in {"weekly", "monthly", "premium"}:
            raise ValueError("only paid plans can be configured")
        if price_stars <= 0 or duration_days <= 0 or searches_per_day <= 0:
            raise ValueError("price, duration, and search limit must be positive")
        if (title_fa is not None and not title_fa.strip()) or (
            title_en is not None and not title_en.strip()
        ):
            raise ValueError("plan titles cannot be empty")
        with self.connection:
            self.connection.execute(
                """
                UPDATE plans SET price_stars=?, duration_days=?, searches_per_day=?,
                    title_fa=COALESCE(?, title_fa),
                    title_en=COALESCE(?, title_en), active=1
                WHERE slug=?
                """,
                (
                    price_stars,
                    duration_days,
                    searches_per_day,
                    title_fa.strip() if title_fa else None,
                    title_en.strip() if title_en else None,
                    slug,
                ),
            )

    def disable_plan(self, slug: str) -> None:
        if slug not in {"trial", "weekly", "monthly", "premium"}:
            raise ValueError("the free plan cannot be disabled")
        with self.connection:
            self.connection.execute(
                "UPDATE plans SET active=0 WHERE slug=?", (slug,)
            )

    def claim_trial(self, user_id: int) -> bool:
        self.ensure_user(user_id)
        plan = self.get_plan("trial")
        if plan is None or not plan["active"]:
            return False
        now = timestamp()
        with self.connection:
            claimed = self.connection.execute(
                "INSERT OR IGNORE INTO trial_claims(user_id, claimed_at) VALUES (?, ?)",
                (user_id, now),
            )
            if claimed.rowcount != 1:
                return False
            self._activate_subscription(
                user_id,
                "trial",
                plan["title_fa"],
                plan["title_en"],
                plan["duration_days"],
                plan["searches_per_day"],
                plan["features_json"],
                now_datetime=utc_now(),
            )
        return True

    def get_subscription(self, user_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT s.*
            FROM subscriptions s
            WHERE s.user_id=? AND s.started_at <= ? AND s.expires_at > ?
            ORDER BY s.started_at DESC LIMIT 1
            """,
            (user_id, timestamp(), timestamp()),
        ).fetchone()

    def get_next_subscription(self, user_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT * FROM subscriptions
            WHERE user_id=? AND started_at > ?
            ORDER BY started_at LIMIT 1
            """,
            (user_id, timestamp()),
        ).fetchone()

    def get_search_limit(self, user_id: int) -> int:
        subscription = self.get_subscription(user_id)
        if subscription:
            return int(subscription["searches_per_day"])
        return int(self.get_plan("free")["searches_per_day"])

    def use_search(self, user_id: int, now: datetime | None = None) -> tuple[bool, int, int]:
        now = now or utc_now()
        day = now.date().isoformat()
        self.ensure_user(user_id)
        limit = self.get_search_limit(user_id)
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO search_usage(user_id, usage_date, searches) "
                "VALUES (?, ?, 0)",
                (user_id, day),
            )
            count = self.connection.execute(
                "SELECT searches FROM search_usage WHERE user_id=? AND usage_date=?",
                (user_id, day),
            ).fetchone()["searches"]
            if count >= limit:
                return False, int(count), limit
            self.connection.execute(
                "UPDATE search_usage SET searches=searches+1 "
                "WHERE user_id=? AND usage_date=?",
                (user_id, day),
            )
            return True, int(count) + 1, limit

    def create_order(self, user_id: int, plan_slug: str) -> dict[str, Any]:
        self.ensure_user(user_id)
        plan = self.get_plan(plan_slug)
        if plan is None or not plan["active"] or plan["price_stars"] <= 0:
            raise ValueError("plan is not available for purchase")
        order_id = uuid.uuid4().hex
        now = timestamp()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO orders(
                    order_id, user_id, plan_slug, title_fa, title_en, amount,
                    currency, duration_days, searches_per_day, features_json,
                    status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    order_id,
                    user_id,
                    plan_slug,
                    plan["title_fa"],
                    plan["title_en"],
                    plan["price_stars"],
                    plan["currency"],
                    plan["duration_days"],
                    plan["searches_per_day"],
                    plan["features_json"],
                    now,
                ),
            )
        return {
            "order_id": order_id,
            "amount": int(plan["price_stars"]),
            "title_fa": plan["title_fa"],
            "title_en": plan["title_en"],
        }

    def get_pending_order(self, order_id: str, user_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM orders WHERE order_id=? AND user_id=? AND status='pending'",
            (order_id, user_id),
        ).fetchone()

    def charge_was_processed(self, charge_id: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM orders WHERE charge_id=?", (charge_id,)
        ).fetchone() is not None

    def mark_order_paid(
        self,
        order_id: str,
        user_id: int,
        currency: str,
        amount: int,
        charge_id: str,
    ) -> bool:
        now = utc_now()
        with self.connection:
            order = self.connection.execute(
                "SELECT * FROM orders WHERE order_id=? AND user_id=? AND status='pending'",
                (order_id, user_id),
            ).fetchone()
            if (
                order is None
                or currency != order["currency"]
                or amount != order["amount"]
                or currency != "XTR"
                or self.connection.execute(
                    "SELECT 1 FROM orders WHERE charge_id=?", (charge_id,)
                ).fetchone()
            ):
                return False
            cursor = self.connection.execute(
                """
                UPDATE orders SET status='paid', paid_at=?, charge_id=?
                WHERE order_id=? AND status='pending'
                """,
                (timestamp(now), charge_id, order_id),
            )
            if cursor.rowcount != 1:
                return False
            self._activate_subscription(
                user_id,
                order["plan_slug"],
                order["title_fa"],
                order["title_en"],
                order["duration_days"],
                order["searches_per_day"],
                order["features_json"],
                now_datetime=now,
            )
        return True

    def _activate_subscription(
        self,
        user_id: int,
        plan_slug: str,
        title_fa: str,
        title_en: str,
        duration_days: int,
        searches_per_day: int,
        features_json: str,
        now_datetime: datetime,
    ) -> None:
        latest_expiry = self.connection.execute(
            "SELECT MAX(expires_at) AS expires_at FROM subscriptions WHERE user_id=?",
            (user_id,),
        ).fetchone()["expires_at"]
        current_expiry = (
            datetime.fromisoformat(latest_expiry) if latest_expiry else now_datetime
        )
        start = max(now_datetime, current_expiry)
        expires = start + timedelta(days=duration_days)
        self.connection.execute(
            """
            INSERT INTO subscriptions(
                user_id, plan_slug, title_fa, title_en, searches_per_day,
                features_json, started_at, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                plan_slug,
                title_fa,
                title_en,
                searches_per_day,
                features_json,
                timestamp(start),
                timestamp(expires),
            ),
        )

    def referral_stats(self, user_id: int) -> tuple[int, list[sqlite3.Row]]:
        total = self.connection.execute(
            "SELECT COUNT(*) AS n FROM referrals WHERE referrer_id=?", (user_id,)
        ).fetchone()["n"]
        rows = self.connection.execute(
            """
            SELECT referred_id, created_at FROM referrals WHERE referrer_id=?
            ORDER BY created_at DESC LIMIT 10
            """,
            (user_id,),
        ).fetchall()
        return int(total), rows

    def order_history(self, user_id: int, limit: int = 5) -> list[sqlite3.Row]:
        return self.connection.execute(
            """
            SELECT order_id, plan_slug, title_fa, title_en, amount, currency,
                   status, created_at, paid_at
            FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    def user_data(self, user_id: int) -> dict[str, Any]:
        user = self.get_user(user_id)
        if user is None:
            return {}
        consent_count = self.connection.execute(
            "SELECT COUNT(*) AS n FROM consents WHERE user_id=?", (user_id,)
        ).fetchone()["n"]
        event_count = self.connection.execute(
            "SELECT COUNT(*) AS n FROM group_events WHERE user_id=?", (user_id,)
        ).fetchone()["n"]
        referral_count = self.connection.execute(
            "SELECT COUNT(*) AS n FROM referrals WHERE referrer_id=?", (user_id,)
        ).fetchone()["n"]
        return {
            "user": user,
            "consent_count": int(consent_count),
            "event_count": int(event_count),
            "referral_count": int(referral_count),
            "activity": self.get_own_activity(user_id),
            "subscription": self.get_subscription(user_id),
            "next_subscription": self.get_next_subscription(user_id),
        }

    def delete_user_data(self, user_id: int) -> None:
        with self.connection:
            # Keep order/charge records for payment reconciliation, but unlink the account.
            self.connection.execute(
                "UPDATE orders SET user_id=NULL, charge_id=NULL WHERE user_id=?",
                (user_id,),
            )
            self.connection.execute("DELETE FROM users WHERE user_id=?", (user_id,))

    def prune_old_events(self, retention_days: int = 90) -> int:
        cutoff = timestamp(utc_now() - timedelta(days=retention_days))
        with self.connection:
            cursor = self.connection.execute(
                "DELETE FROM group_events WHERE occurred_at < ?", (cutoff,)
            )
            self.connection.execute(
                """
                UPDATE groups SET last_event_at = (
                    SELECT MAX(occurred_at) FROM group_events
                    WHERE group_events.chat_id = groups.chat_id
                )
                WHERE last_event_at < ?
                """,
                (cutoff,),
            )
            return cursor.rowcount

    def close(self) -> None:
        self.connection.close()
