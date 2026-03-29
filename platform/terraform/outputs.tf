# Agentic Ads Platform - Terraform Outputs

# =============================================================================
# Service Account
# =============================================================================

output "service_account_email" {
  description = "Email of the platform service account"
  value       = google_service_account.platform.email
}

# =============================================================================
# Cloud Run Services
# =============================================================================

output "agent_service_url" {
  description = "URL of the Agent Cloud Run service"
  value       = module.cloud_run.agent_url
}

output "agent_service_name" {
  description = "Name of the Agent Cloud Run service"
  value       = module.cloud_run.agent_service_name
}

output "scraper_service_url" {
  description = "URL of the Scraper Cloud Run service"
  value       = module.cloud_run.scraper_url
}

output "scraper_service_name" {
  description = "Name of the Scraper Cloud Run service"
  value       = module.cloud_run.scraper_service_name
}

# =============================================================================
# Pub/Sub
# =============================================================================

output "jobs_topic_name" {
  description = "Name of the jobs Pub/Sub topic"
  value       = module.pubsub.jobs_topic_name
}

output "jobs_topic_id" {
  description = "ID of the jobs Pub/Sub topic"
  value       = module.pubsub.jobs_topic_id
}

output "jobs_subscription_name" {
  description = "Name of the jobs Pub/Sub subscription"
  value       = module.pubsub.jobs_subscription_name
}

output "dlq_topic_name" {
  description = "Name of the dead-letter queue topic"
  value       = module.pubsub.dlq_topic_name
}

output "dlq_subscription_name" {
  description = "Name of the dead-letter queue subscription"
  value       = module.pubsub.dlq_subscription_name
}

# =============================================================================
# Cloud Storage
# =============================================================================

output "raw_assets_bucket" {
  description = "Name of the raw assets storage bucket"
  value       = module.storage.raw_bucket_name
}

output "raw_assets_bucket_url" {
  description = "URL of the raw assets storage bucket"
  value       = module.storage.raw_bucket_url
}

output "processed_assets_bucket" {
  description = "Name of the processed assets storage bucket"
  value       = module.storage.processed_bucket_name
}

output "processed_assets_bucket_url" {
  description = "URL of the processed assets storage bucket"
  value       = module.storage.processed_bucket_url
}

# =============================================================================
# Firestore
# =============================================================================

output "firestore_database" {
  description = "Firestore database name"
  value       = google_firestore_database.main.name
}

output "firestore_collections" {
  description = "Firestore collection names"
  value = {
    assets  = "${var.firestore_collection_prefix}_assets"
    jobs    = "${var.firestore_collection_prefix}_jobs"
    metrics = "${var.firestore_collection_prefix}_metrics"
  }
}

# =============================================================================
# Vertex AI
# =============================================================================

output "vertex_ai_endpoint_id" {
  description = "Vertex AI endpoint ID (if deployed)"
  value       = module.vertex_ai.endpoint_id
}

output "vertex_ai_model_id" {
  description = "Vertex AI model ID"
  value       = module.vertex_ai.model_id
}

# =============================================================================
# BigQuery
# =============================================================================

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID"
  value       = var.enable_bigquery ? google_bigquery_dataset.analytics[0].dataset_id : null
}

output "bigquery_tables" {
  description = "BigQuery table IDs"
  value = var.enable_bigquery ? {
    assets = google_bigquery_table.assets[0].table_id
  } : null
}

# =============================================================================
# Environment Configuration
# =============================================================================

output "environment_config" {
  description = "Environment configuration for services"
  value = {
    GCP_PROJECT_ID              = var.project_id
    GCP_REGION                  = var.region
    PUBSUB_TOPIC                = module.pubsub.jobs_topic_name
    PUBSUB_SUBSCRIPTION         = module.pubsub.jobs_subscription_name
    STORAGE_BUCKET_RAW          = module.storage.raw_bucket_name
    STORAGE_BUCKET_PROCESSED    = module.storage.processed_bucket_name
    FIRESTORE_COLLECTION_PREFIX = var.firestore_collection_prefix
    VERTEX_AI_MODEL             = var.vertex_ai_model
  }
  sensitive = false
}

