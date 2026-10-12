/**
 * IAM Least-Privilege Module
 * Enforces principle of least privilege:
 * - Separate service accounts for API and Worker
 * - Publisher permissions strictly scoped to lifecycle topic
 * - Subscriber permissions strictly scoped to worker subscription
 * - Worker permissions strictly scoped to DLQ topic for error routing
 */

# API Gateway Service Account
resource "google_service_account" "api_sa" {
  account_id   = "${var.environment}-identity-api-sa"
  display_name = "Identity Orchestrator API Service Account"
  project      = var.project_id
  description  = "Least-privilege service account for the API Gateway"
}

# Asynchronous Worker Service Account
resource "google_service_account" "worker_sa" {
  account_id   = "${var.environment}-identity-worker-sa"
  display_name = "Identity Orchestrator Worker Service Account"
  project      = var.project_id
  description  = "Least-privilege service account for the Pub/Sub Worker"
}

# API SA: Permission to PUBLISH ONLY to the lifecycle topic
resource "google_pubsub_topic_iam_member" "api_publisher" {
  project = var.project_id
  topic   = var.lifecycle_topic_name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# Worker SA: Permission to SUBSCRIBE to worker subscription
resource "google_pubsub_subscription_iam_member" "worker_subscriber" {
  project      = var.project_id
  subscription = var.worker_subscription_name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.worker_sa.email}"
}

# Worker SA: Permission to PUBLISH to Dead-Letter Topic (DLQ)
resource "google_pubsub_topic_iam_member" "worker_dlq_publisher" {
  project = var.project_id
  topic   = var.dlq_topic_name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}

# Secret Manager Accessor for API (access JWT keys / DB passwords)
resource "google_project_iam_member" "api_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api_sa.email}"
}

# Secret Manager Accessor for Worker
resource "google_project_iam_member" "worker_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.worker_sa.email}"
}
