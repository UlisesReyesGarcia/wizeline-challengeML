variable "project_name" {
  description = "Project name used as prefix for AWS resources."
  type        = string
  default     = "wizeline-challengeml"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region where resources will be deployed."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile used by Terraform. In CI/CD this can be set to null."
  type        = string
  default     = "wizeline-challengeml-dev"
  nullable    = true
}
