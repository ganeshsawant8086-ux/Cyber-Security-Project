output "api_service_uri" {
  value       = google_cloud_run_v2_service.api.uri
  description = "Public or VPC URI of the Cloud Run API Gateway"
}

output "worker_service_uri" {
  value       = google_cloud_run_v2_service.worker.uri
  description = "URI of the Cloud Run Event Worker"
}
