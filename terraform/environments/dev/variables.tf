variable "project_id" {
  type        = string
  description = "GCP Project ID"
  default     = "demo-cloud-security-project"
}

variable "region" {
  type        = string
  description = "GCP Region"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment name"
  default     = "dev"
}

variable "container_image" {
  type        = string
  description = "Container image URI"
  default     = "gcr.io/demo-cloud-security-project/identity-orchestrator:latest"
}

variable "lifecycle_topic_name" {
  type        = string
  default     = "identity-lifecycle-events"
}

variable "dlq_topic_name" {
  type        = string
  default     = "identity-lifecycle-dlq"
}

variable "worker_subscription_name" {
  type        = string
  default     = "identity-lifecycle-worker-sub"
}

variable "opa_url" {
  type        = string
  default     = "http://opa:8181"
}
