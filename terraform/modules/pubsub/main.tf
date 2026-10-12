/**
 * Pub/Sub Module
 * Defines production-ready event bus with dead-letter queue (DLQ),
 * exponential retry backoff, and subscriber dead letter policies.
 */

resource "google_pubsub_topic" "lifecycle_events" {
  name    = var.lifecycle_topic_name
  project = var.project_id

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "identity-orchestrator"
  }
}

resource "google_pubsub_topic" "dead_letter" {
  name    = var.dlq_topic_name
  project = var.project_id

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "identity-orchestrator"
    purpose     = "dead-letter-queue"
  }
}

resource "google_pubsub_subscription" "worker_subscription" {
  name    = var.worker_subscription_name
  project = var.project_id
  topic   = google_pubsub_topic.lifecycle_events.name

  # Acknowledgment deadline before message is redelivered
  ack_deadline_seconds = 60

  # Exponential backoff retry policy
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Route poisonous or failing messages to DLQ after 5 delivery attempts
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  labels = {
    environment = var.environment
    service     = "identity-orchestrator"
  }
}

resource "google_pubsub_subscription" "dlq_subscription" {
  name    = "${var.dlq_topic_name}-sub"
  project = var.project_id
  topic   = google_pubsub_topic.dead_letter.name

  ack_deadline_seconds = 120

  labels = {
    environment = var.environment
    service     = "identity-orchestrator"
  }
}
