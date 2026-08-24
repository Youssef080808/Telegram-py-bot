terraform {
  # Declares which provider plugins this project needs, and which versions
  required_providers {
    aws = {
      source  = "hashicorp/aws" # AWS adress in Terraform Registery
      version = "~> 5.0"        # Accept 5.x updates, but not 6.0
    }
  }

  required_version = ">= 1.5" # Supports any version bigger than or equal to 1.5
}