# Input to bot instance configuration
variable "bot_token" {
  description = "Telegram bot token"
  type        = string
  sensitive   = true # To redact value in plan/apply output
}

variable "instance_name" {
  description = "Value of EC2 instance's Name tag"
  type        = string
  default     = "telegram-bot-server"
}

variable "instance_type" {
  description = "The EC2 instance type"
  type        = string
  default     = "t3.micro"
}