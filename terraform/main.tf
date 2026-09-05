# Configures the AWS provider, credentials come from ~/.aws/credentials
provider "aws" {
  region = "eu-north-1"
}

# Looks up the most recent Amazon Linux 2023 AMI in this region
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}

# Resource type to call AWS to create the security group 
resource "aws_security_group" "bot_sg" {
  name        = "telegram-bot-sg"
  description = "Security group for the Telegram bot instance"

  # Inbound rules
  ingress {
    # SSH only from only one port 22 only from my IP, /32 to allow only a single address 
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["142.169.77.78/32"]
  }

  # Outbound rules - What the instance can reach out to 
  egress {
    # All ports, all protocols and all IPs
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# The EC2 instance that runs the bot container
resource "aws_instance" "bot" {
  ami                    = data.aws_ami.amazon_linux.id   # Which OS the instance boots(Amazon Machine Image)
  instance_type          = var.instance_type              # Hardware size
  key_name               = "telegram-bot-key"             # SSH key
  vpc_security_group_ids = [aws_security_group.bot_sg.id] # List of security groups to attach

  iam_instance_profile = aws_iam_instance_profile.bot_profile.name # Attaches the profile to the instance

  user_data_replace_on_change = true

  user_data = <<-EOF
    #!/bin/bash
    dnf install docker -y
    systemctl enable --now docker
    usermod -aG docker ec2-user

    dnf install cronie -y
    systemctl enable --now crond

    mkdir -p /home/ec2-user/data
    chown ec2-user:ec2-user /home/ec2-user/data

    echo "BOT_TOKEN=${var.bot_token}" > /etc/telegram-bot.env
    chmod 600 /etc/telegram-bot.env

    docker run -d \
        --name telegram-bot \
        --restart unless-stopped \
        --env-file /etc/telegram-bot.env \
        -v /home/ec2-user/data:/data \
        ghcr.io/youssef080808/telegram_bot:latest

    mkdir -p /home/ec2-user/brawl-data
    chown ec2-user:ec2-user /home/ec2-user/brawl-data
    
    echo "BRAWL_API_KEY=${var.brawl_api_key}" > /etc/brawl-api.env
    chmod 600 /etc/brawl-api.env
    
    docker run -d \
        --name brawl-api \
        -p 127.0.0.1:8000:8000 \
        --restart unless-stopped \
        --env-file /etc/brawl-api.env \
        -v /home/ec2-user/brawl-data:/data \
        ghcr.io/youssef080808/brawl-api:latest

    echo '*/30 * * * * docker run --rm --env-file /etc/brawl-api.env -v /home/ec2-user/brawl-data:/data ghcr.io/youssef080808/brawl-api:latest python3 poller.py >> /home/ec2-user/poller.log 2>&1' | crontab -u ec2-user -

  EOF

  tags = {
    Name = var.instance_name # Instance's name in the console
  }
}

# Lets EC2 instances assume this role (data to Read the role)
data "aws_iam_policy_document" "ssm_assume_role" {
  # One rule in IAM policy
  statement {
    # Permits : API call for taking on a role's identity
    actions = ["sts:AssumeRole"]
    # EC2 Sevice is allowed to assume this Role
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# Calls AWS to create IAM Role
resource "aws_iam_role" "bot_ssm_role" {
  name               = "telegram-bot-ssm-role"
  assume_role_policy = data.aws_iam_policy_document.ssm_assume_role.json # The trust policy
}

# AWS-managed policy granting the permissions the SSM Agent needs
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.bot_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" # What the Role can do
}

# The wrapper that attaches a role to an EC2 instance
resource "aws_iam_instance_profile" "bot_profile" {
  name = "telegram-bot-profile"
  role = aws_iam_role.bot_ssm_role.name
}

