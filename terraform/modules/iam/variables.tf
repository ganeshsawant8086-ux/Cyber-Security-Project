variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Environment identifier (dev, staging, prod)"
  default     = "dev"
}

variable "lifecycle_topic_name" {
  type        = string
  description = "Name of the lifecycle Pub/Sub topic"
}

variable "dlq_topic_name" {
  type        = string
  description = "Name of the Dead Letter topic"
}

variable "worker_subscription_name" {
  type        = string
  description = "Name of the worker subscription"
}
