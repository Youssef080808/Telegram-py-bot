terraform {
    # Declares which provider plugins this project needs, and which versions
    required_providers {
        aws = {
            source = "hashicorp/aws" # Where to download the plugin from
            version = "~> 5.0" # Accept 5.x updates, but not 6.0
        }
    }

    required_version = ">= 1.5"
}