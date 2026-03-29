# Agentic Ads Platform - Main Terraform Configuration
#
# This configuration provisions all GCP infrastructure required for the
# agentic ads scraping and reverse-prompting platform.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.10.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.10.0"
    }
  }

  # Configure backend for state storage (uncomment for production)
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "agentic-ads-platform"
  # }
}

# =============================================================================
# Provider Configuration
# =============================================================================

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
  service_name = "agentic-ads"
  labels = {
    project     = "agentic-ads-platform"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# =============================================================================
# Enable Required APIs
# =============================================================================

resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "aiplatform.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "bigquery.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "billingbudgets.googleapis.com",
  ])

  project                    = var.project_id
  service                    = each.value
  disable_dependent_services = false
  disable_on_destroy         = false
}

# =============================================================================
# Service Account
# =============================================================================

resource "google_service_account" "platform" {
  account_id   = "${local.service_name}-sa"
  display_name = "Agentic Ads Platform Service Account"
  description  = "Service account for the agentic ads platform components"
  project      = var.project_id
}

# IAM roles for the service account
resource "google_project_iam_member" "platform_roles" {
  for_each = toset([
    "roles/datastore.user",
    "roles/storage.objectAdmin",
    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
    "roles/aiplatform.user",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/bigquery.dataEditor",
    "roles/secretmanager.secretAccessor",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.platform.email}"
}

# =============================================================================
# Cloud Storage Module
# =============================================================================

module "storage" {
  source = "./modules/storage"

  project_id      = var.project_id
  region          = var.region
  environment     = var.environment
  service_account = google_service_account.platform.email
  labels          = local.labels

  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# Pub/Sub Module
# =============================================================================

module "pubsub" {
  source = "./modules/pubsub"

  project_id      = var.project_id
  environment     = var.environment
  service_account = google_service_account.platform.email
  labels          = local.labels

  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# Firestore Database
# =============================================================================

resource "google_firestore_database" "main" {
  provider = google-beta

  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# Cloud Run Module
# =============================================================================

module "cloud_run" {
  source = "./modules/cloud_run"

  project_id      = var.project_id
  region          = var.region
  environment     = var.environment
  service_account = google_service_account.platform.email
  labels          = local.labels

  # Image references
  agent_image   = var.agent_image
  scraper_image = var.scraper_image

  # Environment configuration
  pubsub_topic        = module.pubsub.jobs_topic_name
  pubsub_subscription = module.pubsub.jobs_subscription_name
  raw_bucket          = module.storage.raw_bucket_name
  processed_bucket    = module.storage.processed_bucket_name

  # Scaling configuration (cost-optimized)
  agent_min_instances   = var.agent_min_instances
  agent_max_instances   = var.agent_max_instances
  scraper_min_instances = var.scraper_min_instances
  scraper_max_instances = var.scraper_max_instances

  # Resource limits (cost-optimized)
  agent_cpu      = var.agent_cpu
  agent_memory   = var.agent_memory
  scraper_cpu    = var.scraper_cpu
  scraper_memory = var.scraper_memory

  depends_on = [
    google_project_service.required_apis,
    module.storage,
    module.pubsub
  ]
}

# =============================================================================
# Vertex AI Module
# =============================================================================

module "vertex_ai" {
  source = "./modules/vertex_ai"

  project_id      = var.project_id
  region          = var.region
  environment     = var.environment
  service_account = google_service_account.platform.email
  labels          = local.labels

  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# BigQuery Dataset (Optional)
# =============================================================================

resource "google_bigquery_dataset" "analytics" {
  count = var.enable_bigquery ? 1 : 0

  dataset_id                 = "creative_ads_analytics"
  friendly_name              = "Agentic Ads Analytics"
  description                = "Analytics dataset for agentic ads platform"
  location                   = var.bigquery_location
  delete_contents_on_destroy = var.environment != "production"

  # Cost optimization: auto-expire tables in non-production environments
  default_table_expiration_ms = var.environment != "production" ? (
    var.bigquery_table_expiration_days * 24 * 60 * 60 * 1000
  ) : null

  labels = local.labels

  access {
    role          = "OWNER"
    user_by_email = google_service_account.platform.email
  }

  depends_on = [google_project_service.required_apis]
}

# BigQuery tables
resource "google_bigquery_table" "assets" {
  count = var.enable_bigquery ? 1 : 0

  dataset_id          = google_bigquery_dataset.analytics[0].dataset_id
  table_id            = "assets"
  deletion_protection = var.environment == "production"

  # Note: Table expiration is inherited from dataset default_table_expiration_ms

  schema = jsonencode([
    {
      name = "asset_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "source"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "industry"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "created_at"
      type = "TIMESTAMP"
      mode = "NULLABLE"
    },
    {
      name = "has_features"
      type = "BOOLEAN"
      mode = "NULLABLE"
    },
    {
      name = "has_prompt"
      type = "BOOLEAN"
      mode = "NULLABLE"
    },
    {
      name = "layout_type"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "focal_point"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "quality_score"
      type = "FLOAT64"
      mode = "NULLABLE"
    }
  ])

  labels = local.labels
}

# =============================================================================
# Cloud Scheduler (for periodic scraping)
# =============================================================================

resource "google_cloud_scheduler_job" "scraping_trigger" {
  count = var.enable_scheduled_scraping ? 1 : 0

  name        = "${local.service_name}-scraping-trigger"
  description = "Trigger periodic scraping jobs"
  schedule    = var.scraping_schedule
  time_zone   = "UTC"
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "${module.cloud_run.agent_url}/trigger"

    oidc_token {
      service_account_email = google_service_account.platform.email
    }
  }

  depends_on = [
    google_project_service.required_apis,
    module.cloud_run
  ]
}

# =============================================================================
# Monitoring & Alerting
# =============================================================================

resource "google_monitoring_alert_policy" "high_error_rate" {
  count = var.enable_monitoring_alerts ? 1 : 0

  display_name = "${local.service_name}-high-error-rate"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run Error Rate > 5%"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "High error rate detected in Agentic Ads Platform services."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "pubsub_dlq" {
  count = var.enable_monitoring_alerts ? 1 : 0

  display_name = "${local.service_name}-dlq-messages"
  combiner     = "OR"

  conditions {
    display_name = "Dead Letter Queue Messages"

    condition_threshold {
      filter          = "resource.type = \"pubsub_subscription\" AND resource.labels.subscription_id = \"${module.pubsub.dlq_subscription_name}\" AND metric.type = \"pubsub.googleapis.com/subscription/num_undelivered_messages\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Messages detected in the dead letter queue. Check for processing failures."
    mime_type = "text/markdown"
  }
}

# =============================================================================
# Budget Alerts (Cost Control)
# =============================================================================

data "google_billing_account" "account" {
  count = var.enable_budget_alerts ? 1 : 0

  billing_account = var.billing_account_id
}

resource "google_billing_budget" "project_budget" {
  count = var.enable_budget_alerts && var.billing_account_id != null ? 1 : 0

  billing_account = var.billing_account_id
  display_name    = "${local.service_name}-${var.environment}-budget"

  budget_filter {
    projects               = ["projects/${var.project_id}"]
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.budget_amount)
    }
  }

  # Create threshold rules for each percentage
  dynamic "threshold_rules" {
    for_each = var.budget_alert_thresholds
    content {
      threshold_percent = threshold_rules.value / 100
      spend_basis       = "CURRENT_SPEND"
    }
  }

  # Email notifications
  dynamic "all_updates_rule" {
    for_each = length(var.budget_alert_emails) > 0 ? [1] : []
    content {
      monitoring_notification_channels = []
      pubsub_topic                     = null
      schema_version                   = "1.0"
      disable_default_iam_recipients   = false
    }
  }
}

# =============================================================================
# Cloud Run Resource Quotas (Additional Cost Control)
# =============================================================================

# Note: Resource quotas are enforced via Cloud Run service configurations
# The max_instances, cpu, and memory limits are set in the cloud_run module

