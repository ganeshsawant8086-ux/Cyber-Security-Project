output "lifecycle_topic_id" {
  value       = google_pubsub_topic.lifecycle_events.id
  description = "Resource ID of the lifecycle Pub/Sub topic"
}

output "lifecycle_topic_name" {
  value       = google_pubsub_topic.lifecycle_events.name
  description = "Name of the lifecycle Pub/Sub topic"
}

output "dlq_topic_id" {
  value       = google_pubsub_topic.dead_letter.id
  description = "Resource ID of the Dead Letter topic"
}

output "worker_subscription_id" {
  value       = google_pubsub_subscription.worker_subscription.id
  description = "Resource ID of the worker subscription"
}
