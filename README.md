# Telegram Planet Python Bot
 
A Telegram bot that fetches and delivers Python blog posts from the [Planet Python](https://planetpython.org/) RSS feed, with search, author lookup, a fully customizable daily digest subscription system, caching, and command logging. Deployed and running live on Railway with persistent storage, containerized with Docker, and built automatically via a GitHub Actions CI pipeline on every push.
 
## Features
 
- Fetches the latest posts from Planet Python's RSS feed
- Search posts by keyword or author (title-based)
- Subscribe to a daily digest, with a per-user post count and delivery time (UTC)
- In-memory caching of the RSS feed (5 minutes) to avoid redundant requests
- Command usage logging to a local file
- Input validation and graceful error handling if the feed is unreachable
- Deployed on Railway with a persistent volume, running continuously and surviving redeploys
- Command menu and description configured via BotFather for discoverability
- Containerized with Docker for consistent, portable builds
- Continuous integration via GitHub Actions, automatically validating the Docker build on every push to `main`
## Commands
 
| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | Lists all available commands with usage examples |
| `/feed [x]` | Sends the latest posts (defaults to 10, max 10) |
| `/random` | Sends one random post from the latest 10 |
| `/search <keyword>` | Finds posts with a keyword in the title |
| `/author <name>` | Finds posts by a specific author |
| `/count` | Shows how many posts are currently available |
| `/subscribe [x]` | Subscribes you to a daily digest (defaults to 10 posts, 16:00 UTC) |
| `/settime <hour> <minute>` | Changes your personal daily digest delivery time (UTC, 24-hour format) |
| `/unsubscribe` | Unsubscribes you from the daily digest |
| `/mysettings` | Shows your current subscription status, post count, and delivery time |
 
## Setup (running your own copy)
 
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
   pip install -r requirements.txt
```
 
4. Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram.
5. Set it as an environment variable (do not hardcode it in `bot.py`):
```bash
   export BOT_TOKEN="your_actual_token_here"
```
 
6. Run the bot:
```bash
   python3 bot.py
```
 
## Running with Docker
 
The bot is fully containerized, so it can also be built and run without setting up a local Python environment.
 
1. Build the image:
```bash
   docker build -t telegram_bot .
```
 
2. Run the container, passing in your bot token and mounting a local folder for persistent data:
```bash
   docker run -e BOT_TOKEN="your_actual_token_here" -v $(pwd)/data:/data telegram_bot
```
 
   - `-e BOT_TOKEN=...` sets the bot token as an environment variable inside the container
   - `-v $(pwd)/data:/data` maps a `data/` folder on the host machine to `/data` inside the container, so `subscribers.json` and `bot.log` persist across container restarts and rebuilds
The image is based on `python:3.11-slim`, installs dependencies from `requirements.txt`, and runs `bot.py` as its entry point.
 
## CI/CD
 
A GitHub Actions workflow (`.github/workflows/build.yml`) automatically builds the Docker image on every push to `main`, catching build-breaking changes immediately instead of relying on manual testing. The workflow:
 
1. Checks out the repository code onto a clean Ubuntu runner
2. Builds the Docker image using the same `Dockerfile` used for local development and deployment
This ensures the containerized build stays valid as the codebase evolves, and provides a foundation for extending the pipeline further (e.g. pushing the image to a container registry, or deploying automatically to a cloud provider).
 
## Deployment
 
The bot is deployed on [Railway](https://railway.app), configured with:
- `BOT_TOKEN` set as an environment variable (never committed to the repo)
- A persistent volume mounted at `/data`
- `DATA_DIR` set to `/data`, so `subscribers.json` and `bot.log` are written to the volume and survive redeploys
- Command menu and bot description set via BotFather (`/setcommands`, `/setdescription`) for a more polished first-time user experience
## Project structure
 
- `bot.py` — entry point; builds the app, registers command handlers, and starts polling
- `planetpy.py` — RSS parsing/caching, all command logic, the logging decorator, and subscriber storage
- `requirements.txt` — dependencies needed for deployment
- `Dockerfile` — defines the container image used for local runs, CI, and deployment
- `.github/workflows/build.yml` — GitHub Actions workflow that builds the Docker image on every push to `main`
- `subscribers.json` — generated at runtime, stores each subscriber's chat ID, post count, and digest time
- `bot.log` — generated at runtime, records every command used with chat ID and timestamp
## How it works
 
- Posts are fetched from `https://planetpython.org/rss20.xml` and parsed with Python's built-in `xml.etree.ElementTree`.
- Fetched posts are cached in memory for 5 minutes to reduce redundant network requests across commands.
- Subscriber data (chat ID, preferred post count, and preferred delivery hour/minute) is stored in `subscribers.json`, written to a persistent volume in production.
- A background job runs every 60 seconds, checking the current UTC time against each subscriber's chosen time and sending their digest the moment it matches — so every subscriber gets their digest at their own chosen time, not a single fixed time for everyone.
- Every command is wrapped with a logging decorator that records the chat ID, command name, and timestamp to `bot.log`.
- The bot runs continuously on Railway, independent of any local machine — subscribers receive their digest on schedule regardless of whether any device is online.
## Notes
 
- Requires Python 3.9+
- Built with [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) and [`requests`](https://pypi.org/project/requests/)
- `subscribers.json` and `bot.log` are generated at runtime and excluded from version control
- All digest times are in UTC; there is currently no per-user timezone conversion