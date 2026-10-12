output "api_service_account_email" {
  value       = google_service_account.api_sa.email
  description = "Email of the API service account"
}

output "worker_service_account_email" {
  value       = google_service_account.worker_sa.email
  description = "Email of the Worker service account"
}
