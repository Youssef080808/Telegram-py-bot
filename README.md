# Telegram Planet Python Bot

A Telegram bot that fetches and delivers Python blog posts from the [Planet Python](https://planetpython.org/) RSS feed, with search, author lookup, a fully customizable daily digest subscription system, caching, and command logging. Subscriber state is stored in SQLite, the app is containerized with Docker, images are built and published to GitHub Container Registry via GitHub Actions, and the AWS EC2 infrastructure is defined in Terraform — a single `terraform apply` provisions the instance and brings the bot up with no manual configuration.

## Features

- Fetches the latest posts from Planet Python's RSS feed
- Search posts by keyword or author (title-based)
- Subscribe to a daily digest, with a per-user post count and delivery time (UTC)
- Subscriber state persisted in SQLite, with parameterized queries throughout
- In-memory caching of the RSS feed (5 minutes) to avoid redundant requests
- Command usage logging to a local file
- Input validation and graceful error handling if the feed is unreachable
- Command menu and description configured via BotFather for discoverability
- Containerized with Docker for consistent, portable builds
- CI/CD via GitHub Actions: every push to `main` builds the image and publishes it to GitHub Container Registry
- AWS infrastructure (EC2 instance and security group) defined as code with Terraform
- Instance self-configures on first boot via a `user_data` script — installs Docker and starts the container automatically
- Runs continuously with an automatic restart policy and a host-mounted volume for persistent data

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

The SQLite database is created automatically on first run — `init_db()` issues a `CREATE TABLE IF NOT EXISTS`, so no separate setup step is needed.

## Data storage

Subscriber state lives in a SQLite database (`subscribers.db`) inside the data directory, in a single table:

```sql
CREATE TABLE IF NOT EXISTS subscribers (
    chat_id TEXT PRIMARY KEY,
    count   INTEGER NOT NULL,
    hour    INTEGER NOT NULL,
    minute  INTEGER NOT NULL
);
```

`chat_id` as the primary key enforces one row per subscriber and indexes lookups. `NOT NULL` constraints mean invalid rows are rejected by the database rather than depending on application-level checks.

Every query is parameterized with `?` placeholders and a separate value tuple, so user input is always treated as data rather than SQL — no string interpolation into queries.

The data access layer exposes targeted operations rather than whole-file reads and writes:

| Function | Operation |
|---|---|
| `get_subscriber(chat_id)` | `SELECT` one row, or `None` |
| `add_subscriber(chat_id, count, hour, minute)` | `INSERT OR REPLACE` |
| `update_time(chat_id, hour, minute)` | `UPDATE`; returns `False` if no row matched |
| `remove_subscriber(chat_id)` | `DELETE` |
| `get_due_subscribers(hour, minute)` | `SELECT` only subscribers whose digest time matches |

`get_due_subscribers` in particular pushes the time filter into the query, so the digest job only receives rows that are actually due instead of loading every subscriber and filtering in Python.

### Migrating from the previous JSON storage

Earlier versions stored subscribers in `subscribers.json`. `migrate_to_sqlite.py` reads that file, if present, and inserts each record into the database. It uses `INSERT OR REPLACE`, so it is safe to run more than once.

Run it against a deployed instance's data volume with:

```bash
docker run --rm \
  -v /home/ec2-user/data:/data \
  -e DATA_DIR=/data \
  ghcr.io/youssef080808/telegram_bot:latest \
  python3 migrate_to_sqlite.py
```

The trailing argument overrides the image's default command, so the container runs the migration and exits instead of starting the bot.

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
   - `-v $(pwd)/data:/data` maps a `data/` folder on the host machine to `/data` inside the container, so `subscribers.db` and `bot.log` persist across container restarts and rebuilds

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

This means build-breaking changes are caught immediately rather than at deploy time, and every commit to `main` produces a pullable artifact that the production server can fetch directly — no manual image transfer between the development machine and the server.

The workflow requests only the permissions it needs (`contents: read` for checkout, `packages: write` for publishing), rather than relying on broader default permissions.

## Infrastructure (Terraform)

The AWS infrastructure is defined as code in `terraform/main.tf` rather than configured by hand through the console, so the environment is version-controlled, reviewable, and reproducible from scratch.

The configuration provisions:

- **A security group** allowing inbound SSH (TCP/22) from a single `/32` address only, with unrestricted egress so the instance can reach the Telegram API, GitHub Container Registry, and the Planet Python feed. Security groups are stateful, so no inbound rules are needed for responses to the bot's own outbound requests.
- **A `t3.micro` EC2 instance** running Amazon Linux 2023, attached to that security group and using an existing EC2 key pair for SSH access.
- **A `user_data` startup script** that runs as root on first boot: it installs and enables Docker, creates the data directory, and starts the bot container with a restart policy. The instance therefore comes up fully configured with no manual steps.

The instance references the security group by attribute (`aws_security_group.bot_sg.id`) rather than by a hardcoded ID, so Terraform resolves the dependency order automatically and creates the security group first. `user_data_replace_on_change = true` is set so that editing the startup script forces instance replacement — otherwise the new script would be stored but never executed, since `user_data` only runs on first boot.

### Secrets

The bot token is declared as a required, `sensitive` input variable rather than hardcoded, so it is redacted in plan and apply output and never committed:

```hcl
variable "bot_token" {
  description = "Telegram bot token"
  type        = string
  sensitive   = true
}
```

The value is supplied via a gitignored `terraform.tfvars` file. Note that `sensitive = true` affects display only — the value is still written to `terraform.tfstate`, which is why that file is also gitignored.

### Usage

```bash
cd terraform
terraform init     # download the AWS provider plugin
terraform plan     # preview changes without applying them
terraform apply    # create or update the infrastructure
```

AWS credentials are read from the local AWS CLI configuration and are never stored in the repository. After a successful apply, the instance's public IP is printed as a Terraform output.

This project was originally deployed on [Railway](https://railway.app) as a managed platform deployment, then migrated to a manually provisioned EC2 instance, and finally to the Terraform-managed infrastructure described here.

## Deployment

Because host configuration lives in the Terraform `user_data` script, deploying from scratch is a single command — `terraform apply` provisions the instance, installs Docker, pulls the image published by CI, and starts the container. The equivalent manual steps, for reference or for running the container elsewhere, are:

```bash
sudo dnf install docker -y
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

docker run -d \
  --name telegram-bot \
  --restart unless-stopped \
  -e BOT_TOKEN="your_actual_token_here" \
  -v /home/ec2-user/data:/data \
  ghcr.io/youssef080808/telegram_bot:latest
```

- `--restart unless-stopped` ensures the bot comes back automatically after a crash or an instance reboot
- `-v /home/ec2-user/data:/data` keeps `subscribers.db` and `bot.log` on the host filesystem, so subscriber state survives container replacement and image upgrades
- `BOT_TOKEN` is passed in at runtime and is never committed to the repository or baked into the image
- Command menu and bot description are set via BotFather (`/setcommands`, `/setdescription`)

Updating to a newer image means pulling the latest tag and recreating the container; the mounted data volume is unaffected. Note that subscriber data lives on the instance's disk, so replacing the instance requires copying `subscribers.db` across.

## Project structure

- `bot.py` — entry point; initializes the database, registers command handlers, and starts polling
- `planetpy.py` — RSS parsing/caching, the SQLite data access layer, all command logic, and the logging decorator
- `migrate_to_sqlite.py` — one-off script that imports records from the legacy `subscribers.json` into the database
- `requirements.txt` — dependencies needed for deployment
- `Dockerfile` — defines the container image used for local runs, CI, and production
- `.github/workflows/build.yml` — GitHub Actions workflow that builds and publishes the image on every push to `main`
- `terraform/main.tf` — Terraform configuration defining the EC2 instance, security group, and startup script
- `subscribers.db` — generated at runtime, stores each subscriber's chat ID, post count, and digest time
- `bot.log` — generated at runtime, records every command used with chat ID and timestamp

## How it works

- Posts are fetched from `https://planetpython.org/rss20.xml` and parsed with Python's built-in `xml.etree.ElementTree`.
- Fetched posts are cached in memory for 5 minutes to reduce redundant network requests across commands.
- Subscriber data is stored in a SQLite database on the mounted volume, so it survives container replacement.
- A background job runs every 60 seconds and queries for subscribers whose configured hour and minute match the current UTC time, sending each their digest — so every subscriber gets their digest at their own chosen time, not a single fixed time for everyone.
- Every command is wrapped with a logging decorator that records the chat ID, command name, and timestamp to `bot.log`.
- The bot runs continuously on the EC2 instance, independent of any local machine — subscribers receive their digest on schedule regardless of whether any device is online.

## Notes

- Requires Python 3.9+
- Built with [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot) and [`requests`](https://pypi.org/project/requests/); SQLite access uses the standard library's `sqlite3` module, so it adds no dependencies
- `subscribers.db` and `bot.log` are generated at runtime and excluded from version control
- All digest times are in UTC; there is currently no per-user timezone conversion
- The SSH ingress rule is pinned to a single IP address in the Terraform config and must be updated when that address changes
- Deployment of a new image is currently a manual pull-and-recreate on the instance; extending the CI pipeline to update the running container would complete the continuous delivery story