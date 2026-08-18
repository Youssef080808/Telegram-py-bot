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
        cidr_blocks = ["156.195.107.186/32"]
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
# Resource type
#resource "aws_instance" "bot" {
 # ami                    = "ami-0c1ac8a41498c1a9c"
 # instance_type          = "t3.micro"
 # key_name               = "telegram-bot-key"
 # vpc_security_group_ids = [aws_security_group.bot_sg.id]

  #tags = {
  #  Name = "telegram-bot-server"
 # }
#}
