# Telegram Planet Python Bot

A Telegram bot that fetches and delivers Python blog posts from the [Planet Python](https://planetpython.org/) RSS feed, with search, author lookup, a fully customizable daily digest subscription system, caching, and command logging.

## Features

- Fetches the latest posts from Planet Python's RSS feed
- Search posts by keyword or author (title-based)
- Subscribe to a daily digest, with a per-user post count and delivery time (UTC)
- In-memory caching of the RSS feed (5 minutes) to avoid redundant requests
- Command usage logging to a local file
- Input validation and graceful error handling if the feed is unreachable

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | Lists all available commands |
| `/feed [x]` | Sends the latest posts (defaults to 10, max 10) |
| `/random` | Sends one random post from the latest 10 |
| `/search <keyword>` | Finds posts with a keyword in the title |
| `/author <name>` | Finds posts by a specific author |
| `/count` | Shows how many posts are currently available |
| `/subscribe [x]` | Subscribes you to a daily digest (defaults to 10 posts, 16:00 UTC) |
| `/settime <hour> <minute>` | Changes your personal daily digest delivery time (UTC, 24-hour format) |
| `/unsubscribe` | Unsubscribes you from the daily digest |
| `/mysettings` | Shows your current subscription status, post count, and delivery time |

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/Youssef080808/Telegram-py-bot.git
   cd Telegram-py-bot
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install "python-telegram-bot[job-queue]" requests
   ```

4. Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram, and paste it into `bot.py`:
   ```python
   BOT_TOKEN = "YOUR_TOKEN_HERE"
   ```

5. Run the bot:
   ```bash
   python3 bot.py
   ```

## Project structure

- `bot.py` — entry point; builds the app, registers command handlers, and starts polling
- `planetpy.py` — RSS parsing/caching, all command logic, the logging decorator, and subscriber storage
- `subscribers.json` — generated at runtime, stores each subscriber's chat ID, post count, and digest time
- `bot.log` — generated at runtime, records every command used with chat ID and timestamp

## How it works

- Posts are fetched from `https://planetpython.org/rss20.xml` and parsed with Python's built-in `xml.etree.ElementTree`.
- Fetched posts are cached in memory for 5 minutes to reduce redundant network requests across commands.
- Subscriber data (chat ID, preferred post count, and preferred delivery hour/minute) is stored locally in `subscribers.json`.
- A background job runs every 60 seconds, checking the current UTC time against each subscriber's chosen time and sending their digest the moment it matches — so every subscriber gets their digest at their own chosen time, not a single fixed time for everyone.
- Every command is wrapped with a logging decorator that records the chat ID, command name, and timestamp to `bot.log`.

## Planned features

- Deployment so the bot runs continuously on a server, not just while the script is active locally

## Notes

- Requires Python 3.9+
- Built with [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) and [`requests`](https://pypi.org/project/requests/)
- `subscribers.json` and `bot.log` are generated at runtime and excluded from version control
- All digest times are in UTC; there is currently no per-user timezone conversion