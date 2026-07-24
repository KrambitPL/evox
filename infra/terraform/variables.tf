variable "aws_region" {
  type        = string
  description = "AWS region for the Evox deployment."
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "image_tag" {
  type        = string
  description = "Immutable Git SHA image tag to deploy."
  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.image_tag))
    error_message = "image_tag must be a full 40-character lowercase Git SHA."
  }
}

variable "api_image_digest" {
  type        = string
  description = "Registry digest of the API/worker image built from image_tag."
  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.api_image_digest))
    error_message = "api_image_digest must be a sha256 registry digest."
  }
}

variable "web_image_digest" {
  type        = string
  description = "Registry digest of the web image built from image_tag."
  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.web_image_digest))
    error_message = "web_image_digest must be a sha256 registry digest."
  }
}

variable "domain_name" {
  type        = string
  description = "ACM-validated public hostname."
}

variable "certificate_arn" {
  type        = string
  description = "ACM certificate ARN in the deployment region for the ALB."
}

variable "cloudfront_certificate_arn" {
  type        = string
  description = "ACM certificate ARN in us-east-1 for CloudFront."
}

variable "hosted_zone_id" {
  type        = string
  description = "Route53 hosted zone ID for domain_name."
}

variable "vpc_id" {
  type        = string
  description = "Existing VPC ID. Network ownership remains outside this module."
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "At least two public subnets for the internet-facing ALB."
  validation {
    condition     = length(var.public_subnet_ids) >= 2
    error_message = "At least two public subnets are required."
  }
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "At least two private subnets for Fargate tasks and EFS."
  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "At least two private subnets are required."
  }
}

variable "api_image_repository" { type = string }
variable "web_image_repository" { type = string }

variable "pioneer_secret_arn" {
  type        = string
  description = "Secrets Manager ARN containing the real Pioneer configuration."
}

variable "sponsor_secret_arn" {
  type        = string
  description = "Secrets Manager ARN containing real Senso, Actian, Band, and Guild configuration."
}

variable "alarm_topic_arn" {
  type        = string
  description = "SNS topic ARN for operational alarm delivery."
}

variable "origin_verify_header" {
  type        = string
  sensitive   = true
  description = "Current private CloudFront-to-ALB verification header."
  validation {
    condition     = length(var.origin_verify_header) >= 32
    error_message = "origin_verify_header must contain at least 32 characters."
  }
}

variable "origin_verify_previous_header" {
  type        = string
  sensitive   = true
  default     = null
  description = "Previous origin header retained temporarily during rotation."
  validation {
    condition     = var.origin_verify_previous_header == null ? true : length(var.origin_verify_previous_header) >= 32
    error_message = "origin_verify_previous_header must be null or contain at least 32 characters."
  }
}
