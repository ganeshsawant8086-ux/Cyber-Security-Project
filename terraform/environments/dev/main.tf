/**
 * Root Terraform Configuration - Development Environment
 *
 * Deploys:
 * 1. Required GCP APIs (Pub/Sub, Cloud Run, Secret Manager)
 * 2. Pub/Sub module (Lifecycle topic, Worker subscription, DLQ topic)
 * 3. IAM module (Least-privilege service accounts and scoped role bindings)
 * 4. Cloud Run module (Containerized API and Worker services)
 */

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required GCP APIs
resource "google_project_service" "enabled_apis" {
  for_each = toset([
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
  ])

  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# 2. Pub/Sub Topics and Subscriptions with DLQ
module "pubsub" {
  source = "../../modules/pubsub"

  project_id                = var.project_id
  environment               = var.environment
  lifecycle_topic_name      = var.lifecycle_topic_name
  dlq_topic_name            = var.dlq_topic_name
  worker_subscription_name  = var.worker_subscription_name

  depends_on = [google_project_service.enabled_apis]
}

# 3. Least-Privilege IAM Service Accounts and Bindings
module "iam" {
  source = "../../modules/iam"

  project_id               = var.project_id
  environment              = var.environment
  lifecycle_topic_name     = module.pubsub.lifecycle_topic_name
  dlq_topic_name           = var.dlq_topic_name
  worker_subscription_name = var.worker_subscription_name

  depends_on = [module.pubsub]
}

# 4. Cloud Run Serverless Services
module "cloud_run" {
  source = "../../modules/cloud_run"

  project_id                   = var.project_id
  region                       = var.region
  environment                  = var.environment
  container_image              = var.container_image
  api_service_account_email    = module.iam.api_service_account_email
  worker_service_account_email = module.iam.worker_service_account_email
  lifecycle_topic_name         = module.pubsub.lifecycle_topic_name
  dlq_topic_name               = var.dlq_topic_name
  opa_url                      = var.opa_url

  depends_on = [module.iam]
}
