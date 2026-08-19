terraform {
    # Declares which provider plugins this project needs, and which versions
    required_providers {
        aws = {
            source = "hashicorp/aws" # Where to download the plugin from
            version = "~> 5.0" # Accept 5.x updates, but not 6.0
        }
    }
}

# Configures the AWS provider, credentials come from ~/.aws/credentials
provider "aws" {
    region = "eu-north-1"
}

# Resource type 
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

  tags = {
    Name = "telegram-bot-server" # Instance's name in the console
  }
}

# To print bot's Public IP after configuring
output "bot_public_ip" {
  description = "Public IP of the bot instance"
  value       = aws_instance.bot.public_ip
}