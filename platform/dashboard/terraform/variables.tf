# =============================================================================
# Agentic Ads Dashboard - Terraform Variables
# =============================================================================

# -----------------------------------------------------------------------------
# Required Variables
# -----------------------------------------------------------------------------

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

# -----------------------------------------------------------------------------
# Service Configuration
# -----------------------------------------------------------------------------

variable "service_name" {
  description = "Base name for the dashboard services"
  type        = string
  default     = "agentic-ads-dashboard"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production"
  }
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

# -----------------------------------------------------------------------------
# API Service Configuration
# -----------------------------------------------------------------------------

variable "api_cpu" {
  description = "CPU limit for API service"
  type        = string
  default     = "1"
}

variable "api_memory" {
  description = "Memory limit for API service"
  type        = string
  default     = "512Mi"
}

variable "api_min_instances" {
  description = "Minimum instances for API service"
  type        = number
  default     = 0
}

variable "api_max_instances" {
  description = "Maximum instances for API service"
  type        = number
  default     = 10
}

# -----------------------------------------------------------------------------
# Frontend Service Configuration
# -----------------------------------------------------------------------------

variable "frontend_cpu" {
  description = "CPU limit for frontend service"
  type        = string
  default     = "1"
}

variable "frontend_memory" {
  description = "Memory limit for frontend service"
  type        = string
  default     = "256Mi"
}

variable "frontend_min_instances" {
  description = "Minimum instances for frontend service"
  type        = number
  default     = 0
}

variable "frontend_max_instances" {
  description = "Maximum instances for frontend service"
  type        = number
  default     = 5
}

# -----------------------------------------------------------------------------
# Backend Configuration
# -----------------------------------------------------------------------------

variable "firestore_collection_prefix" {
  description = "Prefix for Firestore collections"
  type        = string
  default     = "creative_ads"
}

variable "pubsub_topic" {
  description = "Pub/Sub topic for jobs"
  type        = string
  default     = "agentic-ads-jobs"
}

variable "pubsub_subscription" {
  description = "Pub/Sub subscription for jobs"
  type        = string
  default     = "agentic-ads-jobs-sub"
}

variable "agent_service_url" {
  description = "URL of the agent service"
  type        = string
  default     = ""
}

variable "scraper_service_url" {
  description = "URL of the scraper service"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access to the API"
  type        = bool
  default     = true
}

variable "cors_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default     = ["*"]
}

# -----------------------------------------------------------------------------
# Monitoring
# -----------------------------------------------------------------------------

variable "notification_channels" {
  description = "List of notification channel IDs for alerts"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# Environment-specific defaults
# -----------------------------------------------------------------------------

variable "env_config" {
  description = "Environment-specific configuration overrides"
  type = map(object({
    api_min_instances      = number
    api_max_instances      = number
    frontend_min_instances = number
    frontend_max_instances = number
    api_cpu                = string
    api_memory             = string
  }))
  default = {
    development = {
      api_min_instances      = 0
      api_max_instances      = 2
      frontend_min_instances = 0
      frontend_max_instances = 2
      api_cpu                = "1"
      api_memory             = "512Mi"
    }
    staging = {
      api_min_instances      = 1
      api_max_instances      = 5
      frontend_min_instances = 1
      frontend_max_instances = 3
      api_cpu                = "1"
      api_memory             = "1Gi"
    }
    production = {
      api_min_instances      = 2
      api_max_instances      = 20
      frontend_min_instances = 2
      frontend_max_instances = 10
      api_cpu                = "2"
      api_memory             = "2Gi"
    }
  }
}

