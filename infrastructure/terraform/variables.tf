variable "region" { default = "eu-west-2" }
variable "name" { default = "pulseworld-staging" }
variable "vpc_id" { type = string }
variable "public_subnet_ids" {
  type = list(string)
  validation {
    condition = length(var.public_subnet_ids) >= 2
    error_message = "At least two public subnets across AZs are required."
  }
}
variable "private_subnet_ids" {
  type = list(string)
  validation {
    condition = length(var.private_subnet_ids) >= 2
    error_message = "At least two private subnets across AZs are required."
  }
}
variable "certificate_arn" { type = string }
variable "public_origin" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "database_url_secret_arn" {
  type = string
  description = "Secrets Manager ARN with complete URL; provision after RDS creation, never as plaintext Terraform input."
}
variable "provider_secret_arns" {
  type = map(string)
  default = {}
  description = "Environment variable to Secrets Manager ARN; include PULSEPOINT_SECRET and configured provider secrets."
}
variable "desired_count" { default = 1 }
variable "database_multi_az" { default = true }
