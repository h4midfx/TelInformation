import sqlite3
import string
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from bot import build_application
from database import Database, utc_now
from telegram.ext import CallbackQueryHandler, ChatMemberHandler, CommandHandler, PreCheckoutQueryHandler
from translations import TEXT


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.tempdir.name) / "finder.sqlite3")

    def tearDown(self):
        self.database.close()
        self.tempdir.cleanup()

    def test_language_persists_and_invalid_values_are_rejected(self):
        self.database.ensure_user(12345)
        self.assertIsNone(self.database.get_language(12345))
        self.database.set_language(12345, "fa")
        self.assertEqual(self.database.get_language(12345), "fa")
        self.database.set_language(12345, "en")
        self.assertEqual(self.database.get_language(12345), "en")
        with self.assertRaises(ValueError):
            self.database.set_language(12345, "de")
        self.database.close()

        reopened = Database(Path(self.tempdir.name) / "finder.sqlite3")
        self.assertEqual(reopened.get_language(12345), "en")
        reopened.close()

    def test_existing_stage_one_database_is_migrated(self):
        database_path = Path(self.tempdir.name) / "legacy.sqlite3"
        legacy = sqlite3.connect(database_path)
        legacy.execute(
            """
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL CHECK (language IN ('fa', 'en')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        legacy.execute(
            "INSERT INTO users VALUES (?,?,?,?)",
            (88, "fa", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        legacy.commit()
        legacy.close()

        migrated = Database(database_path)
        self.assertEqual(migrated.get_language(88), "fa")
        migrated.ensure_user(89)
        self.assertIsNone(migrated.get_language(89))
        migrated.close()

    def test_events_require_enabled_group_and_prior_explicit_consent(self):
        user_id, chat_id = 101, -1001
        self.database.ensure_user(user_id)
        self.database.upsert_group(chat_id, "Consent Group", "supergroup")
        now = utc_now()

        self.assertFalse(
            self.database.record_group_event(
                chat_id, "Consent Group", "supergroup", user_id, 1, now
            )
        )
        self.database.set_group_enabled(chat_id, True)
        self.database.consent(user_id, chat_id)

        self.assertFalse(
            self.database.record_group_event(
                chat_id, "Consent Group", "supergroup", user_id, 2, now - timedelta(seconds=5)
            )
        )
        event_time = now + timedelta(seconds=2)
        self.assertTrue(
            self.database.record_group_event(
                chat_id, "Consent Group", "supergroup", user_id, 3, event_time
            )
        )
        self.assertFalse(
            self.database.record_group_event(
                chat_id, "Consent Group", "supergroup", user_id, 3, event_time
            )
        )
        self.assertTrue(
            self.database.record_group_event(
                chat_id,
                "Consent Group",
                "supergroup",
                user_id,
                4,
                event_time + timedelta(seconds=1),
            )
        )
        activity = self.database.get_own_activity(user_id)
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0]["event_count"], 2)
        self.assertEqual(activity[0]["title"], "Consent Group")
        self.assertEqual(activity[0]["first_seen"], event_time.isoformat(timespec="seconds"))
        self.assertEqual(
            activity[0]["last_seen"],
            (event_time + timedelta(seconds=1)).isoformat(timespec="seconds"),
        )

        self.database.revoke_consent(user_id, chat_id)
        self.assertFalse(self.database.has_consent(user_id, chat_id))
        self.assertEqual(self.database.get_own_activity(user_id), [])

    def test_catalogue_search_is_limited_to_registered_groups_and_channels(self):
        self.database.upsert_group(-10, "Alpha Group", "group")
        self.database.upsert_group(-20, "News Channel", "channel", catalogued=True)
        self.database.set_group_enabled(-10, True)
        rows = self.database.search_groups("Alpha")
        self.assertEqual([row["title"] for row in rows], ["Alpha Group"])
        rows = self.database.search_groups("News")
        self.assertEqual([row["chat_type"] for row in rows], ["channel"])
        self.assertEqual(rows[0]["event_count"], 0)
        self.assertEqual(len(self.database.list_groups()), 2)

    def test_group_search_escapes_sql_wildcards(self):
        self.database.upsert_group(-1, "100% News", "group", catalogued=True)
        self.database.upsert_group(-2, "100X News", "group", catalogued=True)
        self.assertEqual(
            [row["title"] for row in self.database.search_groups("100%")],
            ["100% News"],
        )

    def test_rate_limit_has_a_fixed_window(self):
        self.database.ensure_user(200)
        start = 1_800_000_000
        self.assertTrue(self.database.consume_rate_limit(200, start, limit=2))
        self.assertTrue(self.database.consume_rate_limit(200, start + 10, limit=2))
        self.assertFalse(self.database.consume_rate_limit(200, start + 20, limit=2))
        self.assertTrue(self.database.consume_rate_limit(200, start + 60, limit=2))

    def test_trial_and_daily_search_quota(self):
        user_id = 300
        self.database.ensure_user(user_id)
        self.assertTrue(self.database.claim_trial(user_id))
        self.assertFalse(self.database.claim_trial(user_id))
        self.assertEqual(self.database.get_search_limit(user_id), 20)
        for _ in range(20):
            self.assertTrue(self.database.use_search(user_id)[0])
        allowed, count, limit = self.database.use_search(user_id)
        self.assertFalse(allowed)
        self.assertEqual((count, limit), (20, 20))

    def test_paid_order_validation_idempotency_and_extension(self):
        user_id = 400
        self.database.ensure_user(user_id)
        self.database.configure_plan("weekly", 50, 7, 30)
        first = self.database.create_order(user_id, "weekly")
        self.assertEqual(
            self.database.get_plan("weekly")["currency"], "XTR"
        )
        self.database.configure_plan(
            "weekly", 75, 14, 100, title_fa="هفتگی جدید", title_en="New Weekly"
        )
        self.assertIsNotNone(self.database.get_pending_order(first["order_id"], user_id))
        self.assertFalse(
            self.database.mark_order_paid(
                first["order_id"], user_id, "XTR", 49, "charge-invalid"
            )
        )
        self.assertTrue(
            self.database.mark_order_paid(
                first["order_id"], user_id, "XTR", 50, "charge-1"
            )
        )
        first_subscription = self.database.get_subscription(user_id)
        expiry_one = first_subscription["expires_at"]
        self.assertEqual(first_subscription["title_en"], "Weekly")
        self.assertEqual(first_subscription["searches_per_day"], 30)
        self.assertFalse(
            self.database.mark_order_paid(
                first["order_id"], user_id, "XTR", 50, "charge-1"
            )
        )

        second = self.database.create_order(user_id, "weekly")
        self.assertTrue(
            self.database.mark_order_paid(
                second["order_id"], user_id, "XTR", 75, "charge-2"
            )
        )
        second_subscription = self.database.get_next_subscription(user_id)
        self.assertIsNotNone(second_subscription)
        expiry_two = second_subscription["expires_at"]
        self.assertGreater(expiry_two, expiry_one)
        self.assertEqual(second_subscription["title_en"], "New Weekly")
        self.assertEqual(second_subscription["searches_per_day"], 100)
        self.assertEqual(second_subscription["started_at"], expiry_one)
        self.assertEqual(self.database.get_search_limit(user_id), 30)
        self.assertEqual(len(self.database.order_history(user_id)), 2)
        with self.assertRaises(ValueError):
            self.database.create_order(user_id, "monthly")

    def test_paid_plans_can_be_disabled_but_free_tier_remains_active(self):
        self.database.configure_plan("weekly", 50, 7, 30)
        self.database.disable_plan("weekly")
        self.assertFalse(self.database.get_plan("weekly")["active"])
        self.assertTrue(self.database.get_plan("free")["active"])
        with self.assertRaises(ValueError):
            self.database.disable_plan("free")
        with self.assertRaises(ValueError):
            self.database.create_order(1, "weekly")
        self.database.disable_plan("trial")
        self.assertFalse(self.database.claim_trial(1))

    def test_referrals_only_record_once_for_existing_distinct_users(self):
        self.database.ensure_user(501)
        self.database.ensure_user(502, referrer_id=501)
        self.database.ensure_user(502, referrer_id=501)
        self.database.ensure_user(503, referrer_id=999)
        self.database.ensure_user(504, referrer_id=504)
        count, history = self.database.referral_stats(501)
        self.assertEqual(count, 1)
        self.assertEqual(history[0]["referred_id"], 502)

    def test_delete_removes_user_data_and_anonymizes_orders(self):
        user_id, chat_id = 600, -600
        self.database.ensure_user(user_id)
        self.database.set_language(user_id, "en")
        self.database.configure_plan("weekly", 50, 7, 30)
        order = self.database.create_order(user_id, "weekly")
        self.database.mark_order_paid(order["order_id"], user_id, "XTR", 50, "charge-6")
        self.database.upsert_group(chat_id, "Private Group", "group")
        self.database.set_group_enabled(chat_id, True)
        self.database.consent(user_id, chat_id)
        self.database.record_group_event(
            chat_id,
            "Private Group",
            "group",
            user_id,
            1,
            utc_now() + timedelta(seconds=1),
        )

        self.database.delete_user_data(user_id)
        self.assertIsNone(self.database.get_user(user_id))
        self.assertIsNone(self.database.get_subscription(user_id))
        order_row = self.database.connection.execute(
            "SELECT user_id, status, charge_id FROM orders WHERE order_id=?",
            (order["order_id"],),
        ).fetchone()
        self.assertIsNone(order_row["user_id"])
        self.assertEqual(order_row["status"], "paid")
        self.assertIsNone(order_row["charge_id"])
        self.assertEqual(
            self.database.connection.execute(
                "SELECT COUNT(*) FROM group_events WHERE user_id=?", (user_id,)
            ).fetchone()[0],
            0,
        )

    def test_event_retention_prunes_only_old_activity(self):
        user_id, chat_id = 700, -700
        self.database.ensure_user(user_id)
        self.database.upsert_group(chat_id, "Retention Group", "group")
        self.database.set_group_enabled(chat_id, True)
        self.database.consent(user_id, chat_id)
        old = utc_now() - timedelta(days=100)
        new = utc_now() + timedelta(seconds=2)
        with self.database.connection:
            self.database.connection.execute(
                "UPDATE consents SET consented_at=? WHERE user_id=? AND chat_id=?",
                ((old - timedelta(days=1)).isoformat(timespec="seconds"), user_id, chat_id),
            )
        self.database.record_group_event(
            chat_id, "Retention Group", "group", user_id, 1, old
        )
        self.database.record_group_event(
            chat_id, "Retention Group", "group", user_id, 2, new
        )
        self.assertEqual(self.database.prune_old_events(90), 1)
        self.assertEqual(self.database.get_own_activity(user_id)[0]["event_count"], 1)

    def test_locales_cover_every_defined_message(self):
        self.assertTrue(TEXT)
        for key, translations in TEXT.items():
            with self.subTest(key=key):
                self.assertEqual(set(translations), {"fa", "en"})
                for language in ("fa", "en"):
                    value = translations[language]
                    self.assertTrue(value)
                    if isinstance(value, str):
                        fields = {
                            field
                            for _, field, _, _ in string.Formatter().parse(value)
                            if field
                        }
                        value.format(**{field: "test" for field in fields})

    def test_application_wires_commands_payments_and_group_membership_updates(self):
        database = Database(":memory:")
        application = build_application(
            "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk", database
        )
        handlers = [
            handler
            for group_handlers in application.handlers.values()
            for handler in group_handlers
        ]
        commands = {
            command
            for handler in handlers
            if isinstance(handler, CommandHandler)
            for command in handler.commands
        }
        self.assertTrue(
            {
                "start",
                "search",
                "data",
                "delete_my_data",
                "subscription",
                "referral",
                "consent",
                "revoke",
                "enable_tracking",
                "disable_tracking",
                "setplan",
                "disableplan",
                "paysupport",
            }.issubset(commands)
        )
        self.assertTrue(any(isinstance(handler, PreCheckoutQueryHandler) for handler in handlers))
        self.assertTrue(any(isinstance(handler, CallbackQueryHandler) for handler in handlers))
        self.assertTrue(any(isinstance(handler, ChatMemberHandler) for handler in handlers))
        database.close()


if __name__ == "__main__":
    unittest.main()
