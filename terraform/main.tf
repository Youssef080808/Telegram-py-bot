# Input to bot instance configuration
variable "bot_token" {
    description = "Telegram bot token"
    type = string
    sensitive = true # To redact value in plan/apply output
}

# Configures the AWS provider, credentials come from ~/.aws/credentials
provider "aws" {
    region = "eu-north-1"
}

# Resource type to call AWS to create the security group 
resource "aws_security_group" "bot_sg" {
    name = "telegram-bot-sg"
    description = "Security group for the Telegram bot instance"

    # Inbound rules
    ingress {
        # SSH only from only one port 22 only from my IP, /32 to allow only a single address 
        description = "SSH from my IP"
        from_port = 22
        to_port = 22
        protocol = "tcp"
        cidr_blocks = ["156.195.49.134/32"]
    }

    # Outbound rules - What the instance can reach out to 
    egress {
        # All ports, all protocols and all IPs
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
}
# The EC2 instance that runs the bot container
resource "aws_instance" "bot" {
  ami                    = "ami-08c6ddb4a5d9d363a" # Which OS the instance boots(Amazon Machine Image)
  instance_type          = "t3.micro" # Hardware size
  key_name               = "telegram-bot-key" # SSH key
  vpc_security_group_ids = [aws_security_group.bot_sg.id] # List of security groups to attach

  iam_instance_profile = aws_iam_instance_profile.bot_profile.name # Attaches the profile to the instance

  user_data_replace_on_change = true

  user_data = <<-EOF
    #!/bin/bash
    dnf install docker -y
    systemctl enable --now docker
    usermod -aG docker ec2-user
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

  EOF

  tags = {
    Name = "telegram-bot-server" # Instance's name in the console
  }
}

# To print bot's Public IP after configuring
output "bot_public_ip" {
  description = "Public IP of the bot instance"
  value       = aws_instance.bot.public_ip
}

# Lets EC2 instances assume this role (data to Read the role)
data "aws_iam_policy_document" "ssm_assume_role" {
    # One rule in IAM policy
    statement {
        # Permits : API call for taking on a role's identity
        actions = ["sts:AssumeRole"]
        # EC2 Sevice is allowed to assume this Role
        principals {
            type = "Service"
            identifiers = ["ec2.amazonaws.com"]
        }
    }
}

# Calls AWS to create IAM Role
resource "aws_iam_role" "bot_ssm_role" {
    name = "telegram-bot-ssm-role"
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