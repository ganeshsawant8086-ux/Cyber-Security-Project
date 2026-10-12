variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type        = string
  description = "GCP Region for Cloud Run"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "dev"
}

variable "container_image" {
  type        = string
  description = "Container image URI in Artifact Registry"
  default     = "gcr.io/demo-cloud-security-project/identity-orchestrator:latest"
}

variable "api_service_account_email" {
  type        = string
  description = "Service account email for API service"
}

variable "worker_service_account_email" {
  type        = string
  description = "Service account email for Worker service"
}

variable "lifecycle_topic_name" {
  type        = string
  description = "Pub/Sub lifecycle topic name"
}

variable "dlq_topic_name" {
  type        = string
  description = "Pub/Sub dead letter topic name"
}

variable "opa_url" {
  type        = string
  description = "Open Policy Agent endpoint URL"
  default     = "http://opa:8181"
}
