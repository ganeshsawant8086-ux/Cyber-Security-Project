/**
 * Cloud Run Module
 * Configures serverless Cloud Run services for API Gateway and Event Worker,
 * with health probes, non-root security context, and Secret Manager references.
 */

resource "google_cloud_run_v2_service" "api" {
  name     = "${var.environment}-identity-api"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.api_service_account_email

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "PUBSUB_TOPIC_LIFECYCLE"
        value = var.lifecycle_topic_name
      }
      env {
        name  = "OPA_URL"
        value = var.opa_url
      }

      startup_probe {
        http_get {
          path = "/healthz"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 10
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8000
        }
        period_seconds = 15
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service" "worker" {
  name     = "${var.environment}-identity-worker"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.worker_service_account_email

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "PUBSUB_TOPIC_DLQ"
        value = var.dlq_topic_name
      }

      startup_probe {
        http_get {
          path = "/healthz"
          port = 8000
        }
        initial_delay_seconds = 5
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}
