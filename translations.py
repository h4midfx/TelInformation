TEXT = {
    "choose_language": {
        "fa": "زبان ربات را انتخاب کنید:",
        "en": "Choose the bot language:",
    },
    "payment_admin": {
        "fa": "پرداخت ستاره‌ای تأیید شد. سفارش: {order_id} | مبلغ: {amount} ستاره | شناسهٔ پرداخت: {charge_id}",
        "en": "Verified Stars payment. Order: {order_id} | Amount: {amount} Stars | Charge: {charge_id}",
    },
    "welcome": {
        "fa": (
            "به Telegram Group Finder خوش آمدید.\n"
            "این ربات فقط داده‌های گروه‌هایی را می‌بیند که به آن اضافه شده و "
            "مدیر گروه ثبت رویداد را فعال کرده باشد. ثبت فعالیت فقط پس از "
            "رضایت صریح هر عضو انجام می‌شود؛ متن پیام ذخیره نمی‌شود.\n"
            "این ربات به همهٔ تلگرام یا پیام‌های خصوصی دیگران دسترسی ندارد."
        ),
        "en": (
            "Welcome to Telegram Group Finder.\n"
            "The bot can only see groups it has been added to where an admin "
            "enabled event recording. Activity is recorded only after each "
            "member explicitly opts in; message content is never stored.\n"
            "The bot cannot access all of Telegram or other people's private messages."
        ),
    },
    "language_saved": {
        "fa": "زبان فارسی ذخیره شد.\n\n",
        "en": "English has been saved.\n\n",
    },
    "menu": {
        "fa": [
            "🔎 جست‌وجو", "👥 گروه‌ها", "📊 داده‌های من", "🗑 حذف داده‌های من",
            "💎 اشتراک", "🎁 دعوت", "🌐 زبان", "❓ راهنما",
        ],
        "en": [
            "🔎 Search", "👥 Groups", "📊 My Data", "🗑 Delete My Data",
            "💎 Subscription", "🎁 Referral", "🌐 Language", "❓ Help",
        ],
    },
    "help": {
        "fa": (
            "راهنما\n\n"
            "برای جست‌وجو، نام گروه ثبت‌شده یا شناسهٔ عددی خودتان را وارد کنید. "
            "جست‌وجوی شناسهٔ اشخاص دیگر در دسترس نیست. مشاهدهٔ رویداد فقط نشان "
            "می‌دهد ربات در زمان ثبت رویداد، فعالیتی از عضوِ رضایت‌داده دیده؛ "
            "عضویت فعلی را اثبات نمی‌کند.\n\n"
            "مدیر گروه می‌تواند با /enable_tracking ثبت را فعال کند. هر عضو "
            "باید در همان گروه /consent بفرستد؛ برای لغو رضایت /revoke را بفرستید. "
            "حذف حساب: دکمهٔ «حذف داده‌های من».\n"
            "پیام‌ها ذخیره نمی‌شوند؛ رویدادهای فعالیت پس از ۹۰ روز پاک می‌شوند."
        ),
        "en": (
            "Help\n\n"
            "Search for a registered group name or your own numeric Telegram ID. "
            "Looking up other people's IDs is not available. A recorded event "
            "only means the bot observed activity from an opted-in member at "
            "that time; it does not prove current membership.\n\n"
            "A group admin can enable recording with /enable_tracking. Each "
            "member must send /consent in that group; use /revoke there to opt "
            "out. Use “Delete My Data” to erase your account data.\n"
            "Messages are not stored; activity events are deleted after 90 days."
        ),
    },
    "language_prompt": {
        "fa": "زبان را انتخاب کنید:",
        "en": "Choose a language:",
    },
    "search_prompt": {
        "fa": "نام گروه ثبت‌شده یا شناسهٔ عددی تلگرام خودتان را بفرستید:",
        "en": "Send a registered group name or your own numeric Telegram ID:",
    },
    "search_other_id": {
        "fa": "برای حفظ حریم خصوصی فقط می‌توانید داده‌های شناسهٔ خودتان را جست‌وجو کنید.",
        "en": "For privacy, you can only search activity linked to your own ID.",
    },
    "search_not_found": {
        "fa": "داده‌ای مطابق این جست‌وجو در سوابق مجاز ربات پیدا نشد.",
        "en": "No matching data was found in the bot's permitted records.",
    },
    "search_results": {
        "fa": "گروه‌ها و کانال‌های ثبت‌شده در همین ربات؛ این نتایج عضویت کاربران را اثبات نمی‌کند:",
        "en": "Groups and channels recorded by this bot; these results do not prove user membership:",
    },
    "activity_header": {
        "fa": "فعالیت ثبت‌شدهٔ شناسهٔ خودتان:",
        "en": "Recorded activity for your own ID:",
    },
    "activity_line": {
        "fa": "{title} — رویداد: {count} | اولین: {first} UTC | آخرین: {last} UTC",
        "en": "{title} — events: {count} | first: {first} UTC | last: {last} UTC",
    },
    "group_search_line": {
        "fa": "• {title} | نوع: {kind} | ثبت در ربات: {registered} UTC | رویدادها: {count} | اولین: {first} UTC | آخرین: {last} UTC",
        "en": "• {title} | type: {kind} | known since: {registered} UTC | events: {count} | first: {first} UTC | last: {last} UTC",
    },
    "activity_source_note": {
        "fa": "منبع: فرادادهٔ پیام‌هایی که این ربات در زمان فعال‌بودن ثبت کرده و عضو برای همان گروه رضایت داده است. زمان‌ها UTC هستند.",
        "en": "Source: message metadata recorded by this bot while enabled, after the member opted in for that group. Times are UTC.",
    },
    "groups_empty": {
        "fa": "هنوز گروهی ثبت و فعال نشده است.",
        "en": "No groups have been registered and enabled yet.",
    },
    "groups_header": {
        "fa": "گروه‌ها و کانال‌های شناخته‌شدهٔ ربات (این فهرست عضویت هیچ کاربری را اثبات نمی‌کند):",
        "en": "Groups and channels known to this bot (this list does not prove any user's membership):",
    },
    "group_line": {
        "fa": "• {title} | شناخته‌شده از: {registered} UTC | رویداد ثبت‌شده: {events} | اعضای رضایت‌داده: {count} | آخرین: {last}",
        "en": "• {title} | known since: {registered} UTC | recorded events: {events} | opted-in users: {count} | latest: {last} UTC",
    },
    "data_header": {
        "fa": "داده‌های ذخیره‌شده برای حساب شما:",
        "en": "Data stored for your account:",
    },
    "data_summary": {
        "fa": "زبان: {language}\nگروه‌های دارای رضایت: {consents}\nرویدادهای فعالیت: {events}\nدعوت‌شدگان: {referrals}",
        "en": "Language: {language}\nGroups with consent: {consents}\nActivity events: {events}\nReferrals: {referrals}",
    },
    "orders_header": {
        "fa": "سفارش‌های اخیر:",
        "en": "Recent orders:",
    },
    "order_line": {
        "fa": "سفارش {order_id} — {plan} — {amount} {currency} — {status} — ایجاد: {created} — پرداخت: {paid}",
        "en": "Order {order_id} — {plan} — {amount} {currency} — {status} — created: {created} — paid: {paid}",
    },
    "order_created": {
        "fa": "سفارش {order_id} ایجاد شد؛ مبلغ {amount} ستاره.",
        "en": "Order {order_id} created; amount: {amount} Stars.",
    },
    "invoice_description": {
        "fa": "اشتراک Telegram Group Finder با پرداخت تلگرام استارز",
        "en": "Telegram Group Finder subscription via Telegram Stars",
    },
    "order_status": {
        "fa": {"pending": "در انتظار پرداخت", "paid": "پرداخت‌شده", "cancelled": "لغوشده"},
        "en": {"pending": "pending", "paid": "paid", "cancelled": "cancelled"},
    },
    "stars_currency": {
        "fa": "ستاره",
        "en": "Stars",
    },
    "not_paid": {
        "fa": "—",
        "en": "—",
    },
    "payment_support": {
        "fa": "برای مشکل پرداخت یا درخواست پشتیبانی با {contact} تماس بگیرید.",
        "en": "For payment issues or support, contact {contact}.",
    },
    "referral_history": {
        "fa": "تاریخچهٔ دعوت‌ها:",
        "en": "Referral history:",
    },
    "referral_line": {
        "fa": "شناسهٔ دعوت‌شده: {user_id} — {created}",
        "en": "Referred ID: {user_id} — {created}",
    },
    "referral_empty": {
        "fa": "هنوز دعوتی ثبت نشده است.",
        "en": "No referrals recorded yet.",
    },
    "no_activity": {
        "fa": "برای حساب شما رویداد گروهی ثبت نشده است.",
        "en": "No group events are recorded for your account.",
    },
    "delete_confirm": {
        "fa": "حذف داده‌ها برگشت‌پذیر نیست. حساب، رضایت‌ها، رویدادها، جست‌وجوها و دعوت‌های شما حذف می‌شوند. رکوردهای پرداخت برای تطبیق مالی ناشناس می‌شوند. ادامه می‌دهید؟",
        "en": "Deletion cannot be undone. Your account, consents, events, searches, and referrals will be deleted. Payment records will be anonymized for reconciliation. Continue?",
    },
    "delete_done": {
        "fa": "داده‌های حساب شما حذف شد. برای استفادهٔ دوباره /start را بفرستید.",
        "en": "Your account data has been deleted. Send /start to use the bot again.",
    },
    "delete_cancelled": {
        "fa": "درخواست حذف لغو شد.",
        "en": "Deletion cancelled.",
    },
    "subscription_header": {
        "fa": "اشتراک و محدودیت جست‌وجوی روزانه:",
        "en": "Subscription and daily search limits:",
    },
    "subscription_current": {
        "fa": "طرح فعلی: {plan}\nانقضا (UTC): {expires}\nسهمیهٔ روزانه: {limit}",
        "en": "Current plan: {plan}\nExpires (UTC): {expires}\nDaily search limit: {limit}",
    },
    "subscription_free": {
        "fa": "طرح فعلی: رایگان\nسهمیهٔ روزانه: {limit}",
        "en": "Current plan: Free\nDaily search limit: {limit}",
    },
    "subscription_scheduled": {
        "fa": "طرح بعدی: {plan}\nشروع (UTC): {starts}\nانقضا (UTC): {expires}\nسهمیهٔ روزانه: {limit}",
        "en": "Next plan: {plan}\nStarts (UTC): {starts}\nExpires (UTC): {expires}\nDaily search limit: {limit}",
    },
    "plan_line": {
        "fa": "{plan} — {price} ستاره | {days} روز | {limit} جست‌وجو در روز | امکانات: {features}",
        "en": "{plan} — {price} Stars | {days} days | {limit} searches/day | Features: {features}",
    },
    "plan_features": {
        "fa": "جست‌وجوی گروه‌های شناخته‌شده، جست‌وجوی فعالیت رضایت‌دادهٔ خود",
        "en": "known-group search, search your own opted-in activity",
    },
    "trial_claimed": {
        "fa": "دورهٔ آزمایشی فعال شد.",
        "en": "Your trial is now active.",
    },
    "trial_already_claimed": {
        "fa": "دورهٔ آزمایشی قبلاً برای این حساب استفاده شده است.",
        "en": "The trial has already been claimed for this account.",
    },
    "plan_unavailable": {
        "fa": "این طرح هنوز برای خرید فعال نشده است.",
        "en": "This plan is not configured for purchase yet.",
    },
    "payment_success": {
        "fa": "پرداخت سفارش {order_id} تأیید شد و اشتراک شما فعال است.",
        "en": "Payment for order {order_id} was verified and your subscription is active.",
    },
    "payment_duplicate": {
        "fa": "این پرداخت قبلاً پردازش شده است.",
        "en": "This payment has already been processed.",
    },
    "payment_invalid": {
        "fa": "اطلاعات پرداخت با سفارش مطابقت ندارد. با پشتیبانی تماس بگیرید.",
        "en": "Payment details do not match the order. Contact support.",
    },
    "referral": {
        "fa": "پیوند دعوت اختصاصی:\n{link}\n\nدعوت‌شده‌ها: {count}\nاین نسخه برای دعوت پاداش مالی ارائه نمی‌کند.",
        "en": "Your referral link:\n{link}\n\nReferrals: {count}\nThis version does not provide a referral cash reward.",
    },
    "rate_limited": {
        "fa": "درخواست‌ها زیاد است. یک دقیقه صبر کنید.",
        "en": "Too many requests. Please wait one minute.",
    },
    "daily_limit": {
        "fa": "سهمیهٔ روزانهٔ شما تمام شده است ({limit}).",
        "en": "Your daily search limit has been reached ({limit}).",
    },
    "tracking_enabled": {
        "fa": "ثبت فعالیت روشن شد. فقط اعضایی ثبت می‌شوند که در گروه /consent بفرستند. متن پیام‌ها ذخیره نمی‌شود و رویدادها ۹۰ روز نگهداری می‌شوند.",
        "en": "Activity recording is enabled. Only members who send /consent in this group are recorded. Message content is not stored; events are retained for 90 days.",
    },
    "tracking_disabled": {
        "fa": "ثبت فعالیت متوقف شد و رویدادها و رضایت‌های این گروه حذف شدند.",
        "en": "Activity recording stopped; this group's events and consents were deleted.",
    },
    "tracking_not_enabled": {
        "fa": "ثبت فعالیت توسط مدیر گروه فعال نشده است.",
        "en": "A group admin has not enabled activity recording.",
    },
    "consent_saved": {
        "fa": "رضایت شما ثبت شد. فقط زمان و تعداد پیام‌های آیندهٔ شما در این گروه ذخیره می‌شود؛ متن پیام‌ها ذخیره نمی‌شود. برای لغو /revoke را بفرستید.",
        "en": "Your consent is recorded. Only the time and count of your future messages in this group will be stored; message content is not stored. Send /revoke to opt out.",
    },
    "consent_revoked": {
        "fa": "رضایت شما لغو و رویدادهای قبلی شما از این گروه حذف شد.",
        "en": "Your consent was revoked and your previous events in this group were deleted.",
    },
    "admin_required": {
        "fa": "این دستور فقط برای مدیران گروه است.",
        "en": "This command is for group admins only.",
    },
    "admin_check_failed": {
        "fa": "امکان تأیید دسترسی مدیر گروه نیست. تنظیمات ربات را بررسی کنید و دوباره تلاش کنید.",
        "en": "Could not verify group-admin access. Check bot permissions and try again.",
    },
    "private_only": {
        "fa": "این دستور را در گفت‌وگوی خصوصی با ربات اجرا کنید.",
        "en": "Please use this command in a private chat with the bot.",
    },
    "unknown": {
        "fa": "از دکمه‌های منو استفاده کنید یا /help را بفرستید.",
        "en": "Use the menu buttons or send /help.",
    },
    "plan_config_usage": {
        "fa": "استفاده: /setplan weekly|monthly|premium price_stars duration_days daily_search_limit [نام_فارسی|English_name]",
        "en": "Usage: /setplan weekly|monthly|premium price_stars duration_days daily_search_limit [Persian_name|English_name]",
    },
    "plan_config_done": {
        "fa": "طرح به‌روزرسانی شد.",
        "en": "Plan updated.",
    },
    "plan_disable_usage": {
        "fa": "استفاده: /disableplan trial|weekly|monthly|premium",
        "en": "Usage: /disableplan trial|weekly|monthly|premium",
    },
    "admin_only": {
        "fa": "این دستور فقط برای مدیر ربات است.",
        "en": "This command is only for the bot admin.",
    },
    "error": {
        "fa": "انجام درخواست ممکن نشد. کمی بعد دوباره تلاش کنید.",
        "en": "The request could not be completed. Please try again later.",
    },
    "help_short": {
        "fa": "دستورها: /start /help /language /search /consent /revoke /enable_tracking /disable_tracking",
        "en": "Commands: /start /help /language /search /consent /revoke /enable_tracking /disable_tracking",
    },
    "support_missing": {
        "fa": "اطلاعات تماس پشتیبانی تنظیم نشده است. لطفاً بعداً دوباره تلاش کنید.",
        "en": "Support contact is not configured. Please try again later.",
    },
}
