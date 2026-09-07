# Telegram Bot: Planet Python Digest + Brawl Stars Tracker

A Telegram bot with two feature sets:

1. **Planet Python digest** — browse, search, and subscribe to a daily digest of the latest posts from [planetpython.org](https://planetpython.org).
2. **Brawl Stars stats** — track a player and query win/loss records and top brawlers, backed by a separate [brawl-stars-api](https://github.com/Youssef080808/brawl-stars-api) service running on the same instance.

## Features

- Fetches and caches the Planet Python RSS feed (5 minutes) to avoid redundant requests
- Search posts by keyword or author, get a random post, or check how many are available
- Per-chat daily digest subscriptions with a configurable post count and delivery time (UTC)
- Brawl Stars player tracking and stats via the companion API
- Every command is logged (chat ID, command, timestamp) to `bot.log`

## Commands

| Command | Description |
|---|---|
| `/feed [x]` | Latest posts (defaults to 10, max 10) |
| `/random` | One random post from the latest 10 |
| `/search <keyword>` | Posts with a keyword in the title |
| `/author <name>` | Posts by a specific author |
| `/count` | How many posts are currently available |
| `/subscribe [x]` | Subscribe to the daily digest (defaults to 10 posts, 16:00 UTC) |
| `/settime <hour> <minute>` | Change your digest delivery time (UTC, 24-hour) |
| `/unsubscribe` | Unsubscribe |
| `/mysettings` | Current subscription status, post count, and delivery time |
| `/bs_track <tag>` | Start tracking a Brawl Stars player |
| `/bs_untrack` | Stop tracking |
| `/bs_stats [filters]` | Win/draw/loss record, filterable by mode/map/type/brawler |
| `/bs_brawlers [filters]` | Best brawlers by win rate, same filters |

## Usage examples

```
/feed 5                          → 5 latest Planet Python posts
/subscribe 3                     → daily digest of 3 posts, 16:00 UTC
/settime 9 30                    → move your digest to 09:30 UTC

/bs_track #GPR920P                → start tracking a player
/bs_stats mode=gemGrab last=50    → record over your last 50 gemGrab battles
/bs_brawlers type=soloRanked      → best brawlers in ranked
```

## Setup

```bash
git clone https://github.com/Youssef080808/Telegram-py-bot.git
cd Telegram-py-bot
python3 -m venv myenv && source myenv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="your_actual_token_here"
python3 bot.py
```

The SQLite database is created automatically on first run.

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | Yes | — | Telegram bot token from BotFather |
| `BRAWL_API_BASE` | No | `http://172.17.0.1:8000` | Base URL of the stats API |
| `DATA_DIR` | No | `.` | Where the SQLite DB and `bot.log` are written |

### Running with Docker

```bash
docker build -t telegram_bot .
docker run -e BOT_TOKEN="your_actual_token_here" -v $(pwd)/data:/data telegram_bot
```

Or pull the published image directly: `ghcr.io/youssef080808/telegram_bot:latest`

## Data storage

Subscriber state lives in SQLite (`subscribers.db`), one row per chat, with `NOT NULL` constraints and parameterized queries throughout. The data access layer exposes targeted operations (`get_subscriber`, `add_subscriber`, `update_time`, `remove_subscriber`, `get_due_subscribers`) rather than reading and rewriting the whole table — `get_due_subscribers` in particular pushes the time filter into the query so the digest job only pulls rows that are actually due.

A one-off `migrate_to_sqlite.py` script imports subscribers from an earlier JSON-based storage format; it's safe to run more than once.

## Deployment

The instance also hosts the [Brawl Stars Stats API](https://github.com/Youssef080808/brawl-stars-api), which this bot calls over HTTP on the Docker bridge network. The two are separate repos with separate images and pipelines, sharing one EC2 instance.

On every push to `main`, GitHub Actions builds the image, publishes it to GHCR, and redeploys the container via AWS Systems Manager — deploys run through SSM rather than SSH, so no SSH key is stored in CI and no inbound port beyond a single IP-restricted SSH rule (used for manual maintenance) is needed.

AWS infrastructure (EC2 instance, security group, IAM role) is defined in Terraform under `/terraform`, and the instance self-configures on first boot via a `user_data` script that installs Docker and starts the container.

This project was originally deployed on Railway, then moved to a manually provisioned EC2 instance, and finally to the Terraform-managed setup described here.

## Project structure

- `bot.py` — entry point; registers command handlers and starts polling
- `planetpy.py` — RSS parsing/caching, SQLite data access, digest scheduling, command logic
- `brawlstars.py` — client for the Brawl Stars stats API
- `migrate_to_sqlite.py` — one-off legacy data migration
- `terraform/` — AWS infrastructure as code
- `.github/workflows/build.yml` — CI/CD pipeline

## Known limitations

- Only one tracked Brawl Stars player per chat is supported
- Subscriber data lives only on the instance's disk with no automated backup
- The SSH ingress rule is pinned to a single IP and needs manual updates if that address changes

## Tech stack

Python, `python-telegram-bot`, SQLite, Docker, Terraform, AWS (EC2, IAM, SSM), GitHub Actions
