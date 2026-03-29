# =============================================================================
# Agentic Ads Dashboard - Terraform Configuration
# =============================================================================
# This configuration deploys the Dashboard infrastructure to GCP including:
# - Cloud Run service for the dashboard API
# - Cloud Run service for the dashboard frontend
# - Service accounts and IAM bindings
# - Monitoring and alerting
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    # Configure via CLI or terraform.tfvars
    # bucket = "your-terraform-state-bucket"
    # prefix = "dashboard"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# =============================================================================
# Local Values
# =============================================================================

locals {
  service_name_api      = "${var.service_name}-api"
  service_name_frontend = "${var.service_name}-frontend"
  
  labels = {
    app         = "agentic-ads-dashboard"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# =============================================================================
# Data Sources
# =============================================================================

data "google_project" "project" {
  project_id = var.project_id
}

# =============================================================================
# Service Account
# =============================================================================

resource "google_service_account" "dashboard" {
  account_id   = "agentic-ads-dashboard"
  display_name = "Agentic Ads Dashboard Service Account"
  description  = "Service account for the Agentic Ads Dashboard"
  project      = var.project_id
}

# IAM roles for the dashboard service account
resource "google_project_iam_member" "dashboard_roles" {
  for_each = toset([
    "roles/datastore.user",            # Firestore access
    "roles/storage.objectViewer",      # Cloud Storage read
    "roles/pubsub.publisher",          # Pub/Sub publish
    "roles/pubsub.subscriber",         # Pub/Sub subscribe
    "roles/monitoring.viewer",         # Cloud Monitoring read
    "roles/logging.viewer",            # Cloud Logging read
    "roles/aiplatform.user",           # Vertex AI access
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.dashboard.email}"
}

# =============================================================================
# Artifact Registry
# =============================================================================

resource "google_artifact_registry_repository" "dashboard" {
  location      = var.region
  repository_id = "agentic-ads-dashboard"
  description   = "Docker images for Agentic Ads Dashboard"
  format        = "DOCKER"
  labels        = local.labels
}

# =============================================================================
# Cloud Run - Dashboard API
# =============================================================================

resource "google_cloud_run_v2_service" "api" {
  name     = local.service_name_api
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.dashboard.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.dashboard.repository_id}/dashboard-api:${var.image_tag}"

      ports {
        container_port = 8000
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
        name  = "GCP_REGION"
        value = var.region
      }

      env {
        name  = "FIRESTORE_COLLECTION_PREFIX"
        value = var.firestore_collection_prefix
      }

      env {
        name  = "PUBSUB_TOPIC"
        value = var.pubsub_topic
      }

      env {
        name  = "PUBSUB_SUBSCRIPTION"
        value = var.pubsub_subscription
      }

      env {
        name  = "AGENT_API_URL"
        value = var.agent_service_url
      }

      env {
        name  = "SCRAPER_API_URL"
        value = var.scraper_service_url
      }

      env {
        name  = "CORS_ORIGINS"
        value = join(",", var.cors_origins)
      }

      env {
        name  = "ENABLE_METRICS"
        value = "true"
      }

      env {
        name  = "ENABLE_CLOUD_LOGGING"
        value = "true"
      }

      resources {
        limits = {
          cpu    = var.api_cpu
          memory = var.api_memory
        }
      }

      startup_probe {
        http_get {
          path = "/ready"
        }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/live"
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 15
      }
    }

    scaling {
      min_instance_count = var.api_min_instances
      max_instance_count = var.api_max_instances
    }

    labels = local.labels
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = local.labels

  depends_on = [google_project_iam_member.dashboard_roles]
}

# Allow unauthenticated access to the API (or configure authentication)
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  count    = var.allow_unauthenticated ? 1 : 0
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =============================================================================
# Cloud Run - Dashboard Frontend
# =============================================================================

resource "google_cloud_run_v2_service" "frontend" {
  name     = local.service_name_frontend
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.dashboard.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.dashboard.repository_id}/dashboard-frontend:${var.image_tag}"

      ports {
        container_port = 80
      }

      env {
        name  = "API_URL"
        value = google_cloud_run_v2_service.api.uri
      }

      resources {
        limits = {
          cpu    = var.frontend_cpu
          memory = var.frontend_memory
        }
      }

      startup_probe {
        http_get {
          path = "/"
        }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 3
      }
    }

    scaling {
      min_instance_count = var.frontend_min_instances
      max_instance_count = var.frontend_max_instances
    }

    labels = local.labels
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = local.labels
}

# Allow unauthenticated access to the frontend
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =============================================================================
# Cloud Monitoring - Uptime Check
# =============================================================================

resource "google_monitoring_uptime_check_config" "api_health" {
  display_name = "Dashboard API Health Check"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = replace(google_cloud_run_v2_service.api.uri, "https://", "")
    }
  }
}

# =============================================================================
# Cloud Monitoring - Alert Policies
# =============================================================================

resource "google_monitoring_alert_policy" "api_error_rate" {
  display_name = "Dashboard API Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error rate above 5%"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${local.service_name_api}\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class != \"2xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Dashboard API error rate is above 5%. Check logs for details."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "604800s"
  }
}

resource "google_monitoring_alert_policy" "api_latency" {
  display_name = "Dashboard API High Latency"
  combiner     = "OR"

  conditions {
    display_name = "Latency above 2s"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${local.service_name_api}\" AND metric.type = \"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2000

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_99"
        cross_series_reducer = "REDUCE_MAX"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Dashboard API P99 latency is above 2 seconds. Check performance."
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "604800s"
  }
}

# =============================================================================
# Cloud Monitoring - Dashboard
# =============================================================================

resource "google_monitoring_dashboard" "dashboard" {
  dashboard_json = jsonencode({
    displayName = "Agentic Ads Dashboard"
    gridLayout = {
      columns = 2
      widgets = [
        {
          title = "API Request Count"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${local.service_name_api}\" AND metric.type = \"run.googleapis.com/request_count\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        },
        {
          title = "API Latency (P99)"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${local.service_name_api}\" AND metric.type = \"run.googleapis.com/request_latencies\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_PERCENTILE_99"
                  }
                }
              }
            }]
          }
        },
        {
          title = "API Instance Count"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${local.service_name_api}\" AND metric.type = \"run.googleapis.com/container/instance_count\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        },
        {
          title = "API CPU Utilization"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${local.service_name_api}\" AND metric.type = \"run.googleapis.com/container/cpu/utilizations\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_PERCENTILE_99"
                  }
                }
              }
            }]
          }
        }
      ]
    }
  })
}
