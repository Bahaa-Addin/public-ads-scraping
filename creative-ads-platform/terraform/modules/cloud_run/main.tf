# Cloud Run Module - Main Configuration

# =============================================================================
# Agent Service (Python)
# =============================================================================

resource "google_cloud_run_v2_service" "agent" {
  name     = "creative-ads-agent"
  location = var.region

  template {
    service_account = var.service_account

    scaling {
      min_instance_count = var.agent_min_instances
      max_instance_count = var.agent_max_instances
    }

    containers {
      image = var.agent_image

      resources {
        limits = {
          cpu    = var.agent_cpu
          memory = var.agent_memory
        }
        cpu_idle = true
      }

      # Environment variables
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
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
        name  = "STORAGE_BUCKET_RAW"
        value = var.raw_bucket
      }
      env {
        name  = "STORAGE_BUCKET_PROCESSED"
        value = var.processed_bucket
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "LOG_LEVEL"
        value = var.environment == "production" ? "INFO" : "DEBUG"
      }

      # Health check
      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        timeout_seconds   = 3
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    # VPC connector if provided
    dynamic "vpc_access" {
      for_each = var.vpc_connector != null ? [1] : []
      content {
        connector = var.vpc_connector
        egress    = "ALL_TRAFFIC"
      }
    }

    timeout = "300s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = var.labels
}

# =============================================================================
# Scraper Service (Node.js)
# =============================================================================

resource "google_cloud_run_v2_service" "scraper" {
  name     = "creative-ads-scraper"
  location = var.region

  template {
    service_account = var.service_account

    scaling {
      min_instance_count = var.scraper_min_instances
      max_instance_count = var.scraper_max_instances
    }

    containers {
      image = var.scraper_image

      resources {
        limits = {
          cpu    = var.scraper_cpu
          memory = var.scraper_memory
        }
        cpu_idle = true
      }

      # Environment variables
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "STORAGE_BUCKET_RAW"
        value = var.raw_bucket
      }
      env {
        name  = "HEADLESS"
        value = "true"
      }
      env {
        name  = "LOG_LEVEL"
        value = var.environment == "production" ? "info" : "debug"
      }

      # Health check
      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 30
        timeout_seconds       = 10
        period_seconds        = 15
        failure_threshold     = 5
      }
    }

    # VPC connector if provided
    dynamic "vpc_access" {
      for_each = var.vpc_connector != null ? [1] : []
      content {
        connector = var.vpc_connector
        egress    = "ALL_TRAFFIC"
      }
    }

    timeout = "600s" # Longer timeout for scraping
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  labels = var.labels
}

# =============================================================================
# IAM - Allow unauthenticated access (if needed)
# =============================================================================

# For internal services, you may want authenticated access only
resource "google_cloud_run_service_iam_member" "agent_invoker" {
  count = var.allow_unauthenticated ? 1 : 0

  location = google_cloud_run_v2_service.agent.location
  service  = google_cloud_run_v2_service.agent.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Allow Pub/Sub to invoke the agent
resource "google_cloud_run_service_iam_member" "agent_pubsub_invoker" {
  location = google_cloud_run_v2_service.agent.location
  service  = google_cloud_run_v2_service.agent.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}

# Allow agent to invoke scraper
resource "google_cloud_run_service_iam_member" "scraper_invoker" {
  location = google_cloud_run_v2_service.scraper.location
  service  = google_cloud_run_v2_service.scraper.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}

