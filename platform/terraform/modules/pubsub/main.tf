# Pub/Sub Module - Main Configuration

locals {
  topic_name     = "agentic-ads-jobs"
  dlq_topic_name = "agentic-ads-jobs-dlq"
}

# =============================================================================
# Main Jobs Topic
# =============================================================================

resource "google_pubsub_topic" "jobs" {
  name    = local.topic_name
  project = var.project_id

  labels = var.labels

  message_retention_duration = "604800s" # 7 days

  # Note: schema_settings requires a Pub/Sub schema resource
  # Uncomment and configure if you need message validation
  # schema_settings {
  #   schema   = google_pubsub_schema.jobs.id
  #   encoding = "JSON"
  # }
}

# =============================================================================
# Dead Letter Queue Topic
# =============================================================================

resource "google_pubsub_topic" "dlq" {
  name    = local.dlq_topic_name
  project = var.project_id

  labels = var.labels

  message_retention_duration = "1209600s" # 14 days
}

# =============================================================================
# Main Jobs Subscription
# =============================================================================

resource "google_pubsub_subscription" "jobs" {
  name    = "${local.topic_name}-sub"
  project = var.project_id
  topic   = google_pubsub_topic.jobs.id

  labels = var.labels

  # Acknowledgment deadline
  ack_deadline_seconds = 300 # 5 minutes for processing

  # Message retention
  message_retention_duration = "604800s" # 7 days
  retain_acked_messages      = false

  # Expiration policy (never expire)
  expiration_policy {
    ttl = ""
  }

  # Dead letter policy
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 5
  }

  # Retry policy with exponential backoff
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Enable exactly once delivery
  enable_exactly_once_delivery = true
}

# =============================================================================
# DLQ Subscription
# =============================================================================

resource "google_pubsub_subscription" "dlq" {
  name    = "${local.dlq_topic_name}-sub"
  project = var.project_id
  topic   = google_pubsub_topic.dlq.id

  labels = var.labels

  ack_deadline_seconds       = 60
  message_retention_duration = "1209600s" # 14 days
  retain_acked_messages      = true       # Keep for analysis

  expiration_policy {
    ttl = ""
  }
}

# =============================================================================
# Feature Extraction Topic
# =============================================================================

resource "google_pubsub_topic" "feature_extraction" {
  name    = "agentic-ads-feature-extraction"
  project = var.project_id

  labels = var.labels

  message_retention_duration = "604800s"
}

resource "google_pubsub_subscription" "feature_extraction" {
  name    = "agentic-ads-feature-extraction-sub"
  project = var.project_id
  topic   = google_pubsub_topic.feature_extraction.id

  labels = var.labels

  ack_deadline_seconds       = 600
  message_retention_duration = "604800s"

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 3
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }
}

# =============================================================================
# Prompt Generation Topic
# =============================================================================

resource "google_pubsub_topic" "prompt_generation" {
  name    = "agentic-ads-prompt-generation"
  project = var.project_id

  labels = var.labels

  message_retention_duration = "604800s"
}

resource "google_pubsub_subscription" "prompt_generation" {
  name    = "agentic-ads-prompt-generation-sub"
  project = var.project_id
  topic   = google_pubsub_topic.prompt_generation.id

  labels = var.labels

  ack_deadline_seconds       = 120
  message_retention_duration = "604800s"

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dlq.id
    max_delivery_attempts = 3
  }
}

# =============================================================================
# IAM - Service Account Permissions
# =============================================================================

resource "google_pubsub_topic_iam_member" "jobs_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.jobs.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${var.service_account}"
}

resource "google_pubsub_subscription_iam_member" "jobs_subscriber" {
  project      = var.project_id
  subscription = google_pubsub_subscription.jobs.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${var.service_account}"
}

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.dlq.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${var.service_account}"
}

