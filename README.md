# Telegram Group Finder

Python-Telegram-Bot 22 project for a privacy-conscious catalogue and search of
Telegram groups/channels known to this bot, with opt-in group activity metadata,
user data controls, referrals, SQLite subscriptions, and Telegram Stars orders.

The bot does **not** search all Telegram, access other people's private messages,
or reveal another person's activity by numeric ID. Users can query only their
own ID. An observed activity event does not prove current membership. This
software makes no claim that information is complete or that subscriptions will
generate income.

## What is implemented

- Persian/English selection saved in SQLite, bilingual menus and user-facing
  messages.
- Group/supergroup metadata is recorded when the bot joins, but becomes
  searchable only after an administrator enables tracking. A channel is
  catalogued when the bot is added to it.
- Group activity is stored only after a group administrator enables tracking
  and each member sends `/consent` in that group. Only sender ID, group ID,
  timestamp and message ID are recorded; no message text is stored. Commands,
  media and channel posts are not activity events.
- `/revoke` in a group removes that member's consent and that group's earlier
  events. `/disable_tracking` removes the group's events and consent records.
- Group/channel catalogue and own activity search are paginated. Numeric ID
  searches are self-only. Searches have a five-per-minute burst limit and the
  current plan's daily quota.
- `/data` and the “My Data” menu show recorded account information. Deletion
  removes account, referrals, consents, activity, search counts and
  subscriptions. Payment orders are unlinked from the account and their charge
  reference is removed; only the anonymized order amount, plan, status and
  timestamps remain for basic reconciliation.
- Free and one-time trial plans; weekly, monthly and premium plans can be
  configured by the bot administrator. Plan duration, Stars price, and daily
  search limit, feature list and active state are stored in SQLite. Paid plans
  can be disabled from new purchases. Expiry is checked using UTC timestamps.
- Telegram Stars invoice orders have unique IDs. Currency, amount, owner and
  pending order are validated both before checkout and after payment; duplicate
  charges do not extend a subscription twice. Plan terms are snapshotted when
  the order is created. Buying another plan while a subscription is active
  schedules it after the current term and shows the upcoming plan in the
  subscription view.
- Referral link/history, and a 90-day retention period for activity events.

## Requirements

- Python 3.10+
- A Telegram bot token from `@BotFather`
- A positive numeric Telegram user ID for administrator-only plan configuration

## Install and run on Windows / VS Code

Open the VS Code terminal as PowerShell and run:

```powershell
Set-Location 'C:\Users\Hamid\Downloads\Telegram Desktop\Telegram Group Finder'
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Open `.env` locally in VS Code. Set `BOT_TOKEN` and `ADMIN_ID` there. Set
`SUPPORT_USERNAME` to a support account without the `@`, or leave it empty to
show that support is not configured. Do not send secrets in chat, paste them
into source code, or commit `.env`. If `.env` already exists, preserve its
values and add only missing settings; do not overwrite it with the example.

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe .\bot.py
```

The bot uses long polling. It works while the computer is running and connected
to the internet; it is not a 24/7 service when Windows sleeps or shuts down.
No paid server is needed for local testing.

## First-run checklist

1. In a private chat, send `/start`, choose فارسی or English, then restart the
   bot and send `/start` again to verify the language persisted.
2. Try `/help`, `/search`, `/data`, `/subscription`, `/referral`, and
   `/delete_my_data` (cancel deletion unless you intend to erase the account).
3. Add the bot to a test group. Promote it to an administrator with only the
   permissions needed to read/respond to messages. In BotFather, disable group
   privacy for this bot if you intend it to observe ordinary group text
   messages; Telegram's privacy settings otherwise limit which messages it
   delivers. Tell group members how recording works before enabling it.
4. A group administrator sends `/enable_tracking`. Each member must then send
   `/consent` in the group. Test `/revoke` and `/disable_tracking`. The bot
   stores no message contents and logs only consenting senders' ordinary
   non-command text message metadata.
5. To catalogue a channel, add the bot as a channel administrator. Channel
   messages and individual subscriber lists are not collected.
6. To configure paid plans, set `ADMIN_ID` in `.env`, start the bot, then send
   this command to the bot in a private chat as that admin:

   ```text
   /setplan weekly 50 7 30
   /setplan monthly 200 30 100
   /setplan premium 500 30 500 ویژه|Premium
   ```

   These examples are sample values in Telegram Stars, not recommendations.
   Choose your own price and limits. Omit the optional final `Persian|English`
   name argument to keep the built-in plan names. Configured plan values become
   available for purchase immediately. Use `/disableplan weekly` (or `monthly`,
   `premium`, `trial`) to stop new purchases/claims. The trial is seven days,
   one claim per account, and the free tier allows five searches per UTC day.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BOT_TOKEN` | required | Token from BotFather |
| `ADMIN_ID` | unset | Positive numeric Telegram ID allowed to configure plans |
| `SUPPORT_USERNAME` | unset | Support username shown by `/paysupport` |
| `DB_PATH` | `data/group_finder.sqlite3` | SQLite database path |

SQLite is stored locally. Back it up securely before moving the bot. It contains
user IDs and order metadata; do not share the database publicly.

## Tests

Run the local test suite from this directory:

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Tests use temporary SQLite databases and never contact Telegram or create a
real payment. Before accepting payments, test the bot in a private test chat
and confirm the BotFather Stars setup, your plan prices, support contact, and
refund/support procedures. There is no automated refund command in this version.

## Privacy and operational limitations

- The bot sees only updates Telegram sends to it in chats where it is present.
- Numeric-ID lookup is restricted to the requesting user's own opt-in records.
- Stored group activity is historical message metadata, not proof of present
  membership or a complete activity history.
- Activity events older than 90 days are deleted at startup. Use `/revoke`,
  `/disable_tracking`, or the account deletion flow for earlier removal.
- This project is not legal advice. Before operating publicly, publish a privacy
  notice appropriate to your jurisdiction and obtain any consent required by
  the group and applicable law.
