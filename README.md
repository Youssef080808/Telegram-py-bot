# Telegram Planet Python Bot

A Telegram bot that fetches and delivers Python blog posts from the [Planet Python](https://planetpython.org/) RSS feed, with search, author lookup, a fully customizable daily digest subscription system, caching, and command logging. Subscriber state is stored in SQLite, the app is containerized with Docker, and the AWS infrastructure is defined in Terraform. A push to `main` builds the image, publishes it to GitHub Container Registry, and redeploys the running container on EC2 — with no SSH access and no inbound ports opened.

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
- Full CI/CD: every push to `main` builds, publishes, and deploys automatically
- AWS infrastructure (EC2 instance, security group, IAM role) defined as code with Terraform
- Instance self-configures on first boot via a `user_data` script — installs Docker and starts the container automatically
- Deployments delivered through AWS Systems Manager, so no SSH keys are stored in CI and no inbound ports are exposed
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

A GitHub Actions workflow (`.github/workflows/build.yml`) runs on every push to `main`, split into two jobs.

### Build

1. Checks out the repository code onto a clean Ubuntu runner
2. Authenticates to GitHub Container Registry using the workflow's automatically provisioned `GITHUB_TOKEN`
3. Builds the Docker image from the same `Dockerfile` used for local development
4. Publishes the image to `ghcr.io/youssef080808/telegram_bot:latest`

The job requests only the permissions it needs (`contents: read` for checkout, `packages: write` for publishing), rather than relying on broader default permissions.

### Deploy

The deploy job declares `needs: build`, so it runs only after a successful build — never against an image that has not been published. It then authenticates to AWS and issues a Systems Manager command instructing the instance to pull the new image and recreate the container:

```bash
aws ssm send-command \
  --instance-ids "$EC2_INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=[
    "docker pull ghcr.io/youssef080808/telegram_bot:latest",
    "docker rm -f telegram-bot",
    "docker run -d --name telegram-bot --restart unless-stopped --env-file /etc/telegram-bot.env -v /home/ec2-user/data:/data ghcr.io/youssef080808/telegram_bot:latest"
  ]'
```

### Why Systems Manager rather than SSH

The obvious way to deploy from CI is to store a private key as a repository secret and have the workflow SSH into the server. That approach has two costs: a key with shell access to production lives in GitHub, and the security group has to permit inbound SSH from GitHub's runner IP ranges, which are broad and change over time.

Systems Manager inverts the direction of the connection. An agent on the instance opens an outbound HTTPS connection to AWS and waits for instructions; AWS hands queued commands to it over that existing channel. As a result:

- No inbound port is opened — the security group still permits SSH from a single IP and nothing else
- No SSH key is stored in CI
- The instance holds no long-lived AWS credentials; an attached IAM role supplies rotating temporary ones

This is the same pattern the bot itself uses. Telegram never connects inbound; the bot polls outbound.

### Credentials and least privilege

Three identities are involved, each scoped to its own job:

| Identity | Purpose | Permissions |
|---|---|---|
| Instance IAM role | Lets the SSM Agent register and receive commands | `AmazonSSMManagedInstanceCore` |
| `github-actions-deploy` IAM user | Lets the workflow issue deploy commands | `ssm:SendCommand`, scoped to one instance ARN and the `AWS-RunShellScript` document, plus read-only access to command results |
| `terraform-user` IAM user | Local infrastructure changes | EC2 and IAM management |

The deploy user's policy names the target instance explicitly, so those credentials cannot reach any other machine in the account even if they leak.

The bot token is never passed through the pipeline. It is written by `user_data` to `/etc/telegram-bot.env` with `chmod 600`, and the container reads it via `--env-file`. The deploy command references the file path rather than the value, so the secret never appears in workflow definitions, SSM command history, or CI logs.

## Infrastructure (Terraform)

The AWS infrastructure is defined as code under `terraform/` rather than configured by hand through the console, so the environment is version-controlled, reviewable, and reproducible from scratch.

The configuration is split by role rather than kept in one file, following the usual Terraform convention:

| File | Contents |
|---|---|
| `terraform.tf` | The `terraform` block: provider requirements and `required_version` |
| `variables.tf` | Input variables and their defaults |
| `main.tf` | Provider configuration, data sources, and resources |
| `outputs.tf` | Values printed after a successful apply |

Terraform reads every `.tf` file in the directory and treats them as a single configuration, so the split is purely for readability.

The configuration provisions:

- **A security group** allowing inbound SSH (TCP/22) from a single `/32` address only, with unrestricted egress so the instance can reach the Telegram API, GitHub Container Registry, AWS Systems Manager, and the Planet Python feed. Security groups are stateful, so no inbound rules are needed for responses to the instance's own outbound requests.
- **A `t3.micro` EC2 instance** running Amazon Linux 2023, attached to that security group and using an existing EC2 key pair for SSH access.
- **An IAM role and instance profile** granting the SSM Agent the permissions it needs. Because this is a role rather than a user, AWS delivers rotating temporary credentials to the instance automatically — no access key is ever written to the server.
- **A `user_data` startup script** that runs as root on first boot: it installs and enables Docker, creates the data directory, writes the bot token to a root-only environment file, and starts the container with a restart policy. The instance therefore comes up fully configured with no manual steps.

### Resolving the AMI dynamically

The machine image is looked up at plan time rather than hardcoded:

```hcl
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}
```

This keeps the configuration current as Amazon publishes new releases, and removes a value that would otherwise silently go stale. The trade-off is that a new upstream release changes the resolved ID, and since `ami` forces replacement, a plan can propose destroying and recreating the instance even when nothing in the configuration changed. Pinning a specific AMI avoids that surprise at the cost of drifting out of date; this project accepts the churn in exchange for staying current, and the runbook below covers the data handling that replacement requires.

The instance references the security group, instance profile, and AMI by attribute rather than by hardcoded IDs, so Terraform resolves the dependency order automatically. `user_data_replace_on_change = true` is set so that editing the startup script forces instance replacement — otherwise the new script would be stored but never executed, since `user_data` only runs on first boot.

### Variables and version pinning

Values that might reasonably change are declared as input variables with sensible defaults, rather than being scattered through the resource blocks:

```hcl
variable "instance_type" {
  description = "The EC2 instance type"
  type        = string
  default     = "t3.micro"
}
```

Both the provider and the Terraform CLI itself are version-constrained, so a future release cannot silently change how this configuration behaves:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"   # accept 5.x, but not 6.0
    }
  }

  required_version = ">= 1.5"
}
```

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

AWS credentials are read from the local AWS CLI configuration and are never stored in the repository.

After a successful apply, the instance's public IP and ID are exposed as outputs, so neither has to be looked up in the console:

```bash
terraform output                    # both values
terraform output bot_public_ip      # just the IP
terraform output ec2_instance_id    # just the instance ID
```

This project was originally deployed on [Railway](https://railway.app) as a managed platform deployment, then migrated to a manually provisioned EC2 instance, and finally to the Terraform-managed infrastructure described here.

## Deployment

Routine deploys require no manual action: pushing to `main` builds the image and redeploys the container automatically.

Provisioning from scratch is a single `terraform apply`, which creates the instance and brings the bot up via the `user_data` script. The equivalent manual steps, for reference or for running the container elsewhere, are:

```bash
sudo dnf install docker -y
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

docker run -d \
  --name telegram-bot \
  --restart unless-stopped \
  --env-file /etc/telegram-bot.env \
  -v /home/ec2-user/data:/data \
  ghcr.io/youssef080808/telegram_bot:latest
```

- `--restart unless-stopped` ensures the bot comes back automatically after a crash or an instance reboot
- `-v /home/ec2-user/data:/data` keeps `subscribers.db` and `bot.log` on the host filesystem, so subscriber state survives container replacement and image upgrades
- `--env-file /etc/telegram-bot.env` supplies the bot token from a root-only file written at provisioning time, so it is never baked into the image or passed through CI

### Replacing the instance

Changing `ami` or `user_data` forces Terraform to destroy and recreate the instance, taking its disk with it. Subscriber data lives on that disk, so it has to be carried across by hand.

**Before applying**, copy the database off and confirm it actually contains rows — a database with a schema and no rows is the same size and passes every superficial check:

```bash
scp -i ~/Desktop/telegram-bot-key.pem ec2-user@OLD_IP:/home/ec2-user/data/subscribers.db ~/Desktop/subscribers-backup.db
sqlite3 ~/Desktop/subscribers-backup.db "SELECT * FROM subscribers;"
```

**After applying**, the new instance has already run `user_data`, so the bot is running and has created an empty `subscribers.db` owned by root. Restoring therefore needs the container stopped and a privileged move, rather than a direct overwrite:

```bash
# From the local machine — copy to the home directory, which ec2-user can write
scp -i ~/Desktop/telegram-bot-key.pem ~/Desktop/subscribers-backup.db ec2-user@NEW_IP:/home/ec2-user/

# On the instance
docker stop telegram-bot
sudo mv /home/ec2-user/subscribers-backup.db /home/ec2-user/data/subscribers.db
docker start telegram-bot

# Confirm the rows are readable through the application's own data layer
docker exec telegram-bot python3 -c "import planetpy as p; print(p.get_subscriber('CHAT_ID'))"
```

Copying directly into `data/` fails with a permission error because the running container created the file as root, and copying while the container is running risks the open SQLite handle overwriting what was just restored.

Replacement also changes the instance's IP and ID. Both are available from the outputs:

```bash
terraform output
```

The new instance ID must then be updated in two places before the next deploy will work:

1. The `EC2_INSTANCE_ID` repository secret
2. The instance ARN in the `github-actions-ssm-deploy` IAM policy

## Project structure

- `bot.py` — entry point; initializes the database, registers command handlers, and starts polling
- `planetpy.py` — RSS parsing/caching, the SQLite data access layer, all command logic, and the logging decorator
- `migrate_to_sqlite.py` — one-off script that imports records from the legacy `subscribers.json` into the database
- `requirements.txt` — dependencies needed for deployment
- `Dockerfile` — defines the container image used for local runs, CI, and production
- `.github/workflows/build.yml` — GitHub Actions workflow that builds, publishes, and deploys on every push to `main`
- `terraform/terraform.tf` — Terraform settings and provider version constraints
- `terraform/variables.tf` — input variables (bot token, instance type, instance name)
- `terraform/main.tf` — the EC2 instance, security group, IAM role, AMI lookup, and startup script
- `terraform/outputs.tf` — the instance's public IP and ID, printed after apply
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

### Known limitations

- Subscriber data is not backed up automatically. It lives only on the instance's root volume, so instance replacement requires the manual runbook above, and an instance failure would lose it outright. Scheduled snapshots, or moving the database onto a separate EBS volume that survives replacement, would address this.
- Instance replacement requires manually updating the `EC2_INSTANCE_ID` secret and the deploy policy's instance ARN. Targeting by tag rather than by instance ID would remove both steps.
- The SSH ingress rule is pinned to a single IP address and must be updated when that address changes. An `http` data source resolving the current address at plan time would remove the manual step.
- `terraform.tfstate` is stored locally rather than in a remote backend, so it is not shared or locked. An S3 backend with DynamoDB locking would be the standard fix.
- `terraform-user` currently holds `IAMFullAccess`, which is broader than the role and policy management this project actually needs.
- The deploy job reports success once Systems Manager accepts the command, not once the container is confirmed healthy. Polling `ssm:GetCommandInvocation` for the result would close that gap.