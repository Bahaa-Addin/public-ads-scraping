# Agentic Ads Platform - Terraform Variables

# =============================================================================
# Required Variables
# =============================================================================

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

# =============================================================================
# Environment Configuration
# =============================================================================

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

# =============================================================================
# Service Account
# =============================================================================

variable "service_account_email" {
  description = "Custom service account email (optional, will create one if not provided)"
  type        = string
  default     = null
}

# =============================================================================
# Container Images
# =============================================================================

variable "agent_image" {
  description = "Docker image for the Python agent service"
  type        = string
  default     = "gcr.io/PROJECT_ID/agentic-ads-agent:latest"
}

variable "scraper_image" {
  description = "Docker image for the Node.js scraper service"
  type        = string
  default     = "gcr.io/PROJECT_ID/agentic-ads-scraper:latest"
}

# =============================================================================
# Cloud Run Scaling
# =============================================================================

variable "agent_min_instances" {
  description = "Minimum instances for the agent service"
  type        = number
  default     = 0
}

variable "agent_max_instances" {
  description = "Maximum instances for the agent service (set low for cost control)"
  type        = number
  default     = 1
}

variable "scraper_min_instances" {
  description = "Minimum instances for the scraper service"
  type        = number
  default     = 0
}

variable "scraper_max_instances" {
  description = "Maximum instances for the scraper service (set low for cost control)"
  type        = number
  default     = 1
}

# =============================================================================
# Firestore Configuration
# =============================================================================

variable "firestore_location" {
  description = "Firestore database location"
  type        = string
  default     = "nam5"
}

variable "firestore_collection_prefix" {
  description = "Prefix for Firestore collections"
  type        = string
  default     = "creative_ads"
}

# =============================================================================
# BigQuery Configuration
# =============================================================================

variable "enable_bigquery" {
  description = "Enable BigQuery for analytics"
  type        = bool
  default     = true
}

variable "bigquery_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

variable "bigquery_table_expiration_days" {
  description = "Days until BigQuery tables expire (for non-production cost control)"
  type        = number
  default     = 30
}

# =============================================================================
# Vertex AI Configuration
# =============================================================================

variable "vertex_ai_model" {
  description = "Vertex AI model to use for reverse prompting"
  type        = string
  default     = "gemini-1.5-pro"
}

# =============================================================================
# Scheduled Scraping
# =============================================================================

variable "enable_scheduled_scraping" {
  description = "Enable Cloud Scheduler for periodic scraping"
  type        = bool
  default     = false
}

variable "scraping_schedule" {
  description = "Cron schedule for periodic scraping"
  type        = string
  default     = "0 */6 * * *" # Every 6 hours
}

# =============================================================================
# Monitoring & Alerting
# =============================================================================

variable "enable_monitoring_alerts" {
  description = "Enable Cloud Monitoring alerts"
  type        = bool
  default     = true
}

variable "notification_channels" {
  description = "List of notification channel IDs for alerts"
  type        = list(string)
  default     = []
}

# =============================================================================
# Network Configuration
# =============================================================================

variable "vpc_connector" {
  description = "VPC connector for private connectivity (optional)"
  type        = string
  default     = null
}

# =============================================================================
# Resource Limits (Cost-Optimized for Testing)
# =============================================================================

variable "agent_cpu" {
  description = "CPU allocation for agent service"
  type        = string
  default     = "0.25"
}

variable "agent_memory" {
  description = "Memory allocation for agent service"
  type        = string
  default     = "512Mi"
}

variable "scraper_cpu" {
  description = "CPU allocation for scraper service"
  type        = string
  default     = "0.25"
}

variable "scraper_memory" {
  description = "Memory allocation for scraper service"
  type        = string
  default     = "512Mi"
}

# =============================================================================
# Budget Alerts
# =============================================================================

variable "enable_budget_alerts" {
  description = "Enable GCP budget alerts for cost monitoring"
  type        = bool
  default     = true
}

variable "budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 50
}

variable "budget_alert_thresholds" {
  description = "Budget alert thresholds as percentages"
  type        = list(number)
  default     = [50, 80, 100]
}

variable "budget_alert_emails" {
  description = "Email addresses to receive budget alerts"
  type        = list(string)
  default     = []
}

variable "billing_account_id" {
  description = "GCP Billing Account ID for budget alerts (format: XXXXXX-XXXXXX-XXXXXX)"
  type        = string
  default     = null
}

