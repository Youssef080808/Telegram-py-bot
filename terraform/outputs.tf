# To print bot's Public IP after configuring
output "bot_public_ip" {
  description = "Public IP of the bot instance"
  value       = aws_instance.bot.public_ip
}

# To print the EC2 instance ID after apply
output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.bot.id
}