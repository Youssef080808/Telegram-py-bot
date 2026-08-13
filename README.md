# Telegram Planet Python Bot

A Telegram bot that fetches and delivers Python blog posts from the [Planet Python](https://planetpython.org/) RSS feed, with search, author lookup, and a daily digest subscription system.

## Features

- Fetches the latest posts from Planet Python's RSS feed
- Search posts by keyword or author (title-based)
- Subscribe to a daily digest, sent automatically at a set time
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
| `/subscribe [x]` | Subscribes you to a daily digest (defaults to 10 posts) |
| `/unsubscribe` | Unsubscribes you from the daily digest |

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
   pip install python-telegram-bot requests
   ```

4. Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram, and paste it into `bot.py`:
   ```python
   BOT_TOKEN = "YOUR_TOKEN_HERE"
   ```

5. Run the bot:
   ```bash
   python3 bot.py
   ```

## How it works

- Posts are fetched from `https://planetpython.org/rss20.xml` and parsed with Python's built-in `xml.etree.ElementTree`.
- Subscriber data (chat ID + preferred post count) is stored locally in `subscribers.json`.
- The daily digest is sent automatically using `python-telegram-bot`'s job queue — no manual trigger needed once subscribed.

## Planned features

- Caching the RSS feed for a few minutes to avoid redundant requests
- A Brawl Stars integration (map lookups, brawler info) as a separate command set
- Logging of command usage
- Simple deployment so the bot runs continuously, not just while the script is active locally

## Notes

- Requires Python 3.9+
- Built with [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) and [`requests`](https://pypi.org/project/requests/)