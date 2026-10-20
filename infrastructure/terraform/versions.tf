terraform {
  required_version = ">= 1.6, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  # Configure an encrypted, access-controlled remote state backend before apply.
}
provider "aws" { region = var.region }
