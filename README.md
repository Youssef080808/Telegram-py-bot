# Telegram Planet Python Bot

A Telegram bot that fetches and delivers Python blog posts from the [Planet Python](https://planetpython.org/) RSS feed, with search, author lookup, a fully customizable daily digest subscription system, caching, and command logging. Containerized with Docker, built and published to GitHub Container Registry automatically via GitHub Actions, and deployed as a self-managed container on an AWS EC2 instance with persistent storage.

## Features

- Fetches the latest posts from Planet Python's RSS feed
- Search posts by keyword or author (title-based)
- Subscribe to a daily digest, with a per-user post count and delivery time (UTC)
- In-memory caching of the RSS feed (5 minutes) to avoid redundant requests
- Command usage logging to a local file
- Input validation and graceful error handling if the feed is unreachable
- Command menu and description configured via BotFather for discoverability
- Containerized with Docker for consistent, portable builds
- CI/CD via GitHub Actions: every push to `main` builds the image and publishes it to GitHub Container Registry
- Deployed on AWS EC2, running continuously with an automatic restart policy and a host-mounted volume for persistent data

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

The image is based on `python:3.11-slim`, installs dependencies from `requirements.txt`, sets `DATA_DIR=/data`, and runs `bot.py` as its entry point.

Alternatively, the pre-built image can be pulled directly from GitHub Container Registry instead of building locally:

```bash
docker pull ghcr.io/youssef080808/telegram_bot:latest
```

## CI/CD

A GitHub Actions workflow (`.github/workflows/build.yml`) runs on every push to `main` and:

1. Checks out the repository code onto a clean Ubuntu runner
2. Authenticates to GitHub Container Registry using the workflow's automatically provisioned `GITHUB_TOKEN`
3. Builds the Docker image from the same `Dockerfile` used for local development
4. Publishes the image to `ghcr.io/youssef080808/telegram_bot:latest`

This means build-breaking changes are caught immediately rather than at deploy time, and every commit to `main` produces a versioned, pullable artifact that the production server can fetch directly — no manual image transfer between the development machine and the server.

The workflow requests only the permissions it needs (`contents: read` for checkout, `packages: write` for publishing), rather than relying on broader default permissions.

## Deployment

The bot was originally deployed on [Railway](https://railway.app) as a managed platform deployment, and was later migrated to **AWS EC2** to run as a self-managed container with direct control over the host environment.

Current production setup:

- A `t3.micro` EC2 instance running Amazon Linux 2023, with Docker installed and enabled via `systemd` so the Docker daemon starts automatically on reboot
- The container image is pulled directly from GitHub Container Registry, so the server runs exactly the artifact produced by CI:
  ```bash
  docker pull ghcr.io/youssef080808/telegram_bot:latest
  ```
- The container is started in detached mode with a restart policy and a host-mounted data volume:
  ```bash
  docker run -d \
    --name telegram-bot \
    --restart unless-stopped \
    -e BOT_TOKEN="your_actual_token_here" \
    -v /home/ec2-user/data:/data \
    ghcr.io/youssef080808/telegram_bot:latest
  ```
- `--restart unless-stopped` ensures the bot comes back automatically after a crash or an instance reboot
- `-v /home/ec2-user/data:/data` keeps `subscribers.json` and `bot.log` on the host filesystem, so subscriber state survives container replacement and image upgrades
- `BOT_TOKEN` is passed in at runtime as an environment variable and is never committed to the repository or baked into the image
- Inbound access is restricted by an EC2 security group allowing SSH (port 22) from a single IP only; no other ports are exposed, since the bot polls Telegram outbound rather than serving inbound traffic
- Command menu and bot description set via BotFather (`/setcommands`, `/setdescription`) for a more polished first-time user experience

Deploying an updated version is a matter of pulling the latest image and recreating the container; the mounted data volume is unaffected.

## Project structure

- `bot.py` — entry point; builds the app, registers command handlers, and starts polling
- `planetpy.py` — RSS parsing/caching, all command logic, the logging decorator, and subscriber storage
- `requirements.txt` — dependencies needed for deployment
- `Dockerfile` — defines the container image used for local runs, CI, and production
- `.github/workflows/build.yml` — GitHub Actions workflow that builds and publishes the image on every push to `main`
- `subscribers.json` — generated at runtime, stores each subscriber's chat ID, post count, and digest time
- `bot.log` — generated at runtime, records every command used with chat ID and timestamp

## How it works

- Posts are fetched from `https://planetpython.org/rss20.xml` and parsed with Python's built-in `xml.etree.ElementTree`.
- Fetched posts are cached in memory for 5 minutes to reduce redundant network requests across commands.
- Subscriber data (chat ID, preferred post count, and preferred delivery hour/minute) is stored in `subscribers.json`, written to a host-mounted volume in production.
- A background job runs every 60 seconds, checking the current UTC time against each subscriber's chosen time and sending their digest the moment it matches — so every subscriber gets their digest at their own chosen time, not a single fixed time for everyone.
- Every command is wrapped with a logging decorator that records the chat ID, command name, and timestamp to `bot.log`.
- The bot runs continuously on the EC2 instance, independent of any local machine — subscribers receive their digest on schedule regardless of whether any device is online.

## Notes

- Requires Python 3.9+
- Built with [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) and [`requests`](https://pypi.org/project/requests/)
- `subscribers.json` and `bot.log` are generated at runtime and excluded from version control
- All digest times are in UTC; there is currently no per-user timezone conversion
- Subscriber state is currently stored in a JSON file, which is sufficient at the current scale; migrating to SQLite would be the natural next step for concurrent writes and querying