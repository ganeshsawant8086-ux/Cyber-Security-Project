variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, staging, prod)"
  default     = "dev"
}

variable "lifecycle_topic_name" {
  type        = string
  description = "Name of the primary identity lifecycle topic"
  default     = "identity-lifecycle-events"
}

variable "dlq_topic_name" {
  type        = string
  description = "Name of the dead letter topic"
  default     = "identity-lifecycle-dlq"
}

variable "worker_subscription_name" {
  type        = string
  description = "Name of the pull/push subscription for the worker"
  default     = "identity-lifecycle-worker-sub"
}
