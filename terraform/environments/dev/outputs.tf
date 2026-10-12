output "lifecycle_topic_name" {
  value       = module.pubsub.lifecycle_topic_name
  description = "Pub/Sub lifecycle topic"
}

output "api_service_account" {
  value       = module.iam.api_service_account_email
  description = "Service account running API"
}

output "worker_service_account" {
  value       = module.iam.worker_service_account_email
  description = "Service account running Worker"
}

output "api_endpoint_uri" {
  value       = module.cloud_run.api_service_uri
  description = "Cloud Run API Service URL"
}
