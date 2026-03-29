# Vertex AI Module - Variables

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "service_account" {
  description = "Service account email"
  type        = string
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}

variable "enable_feature_store" {
  description = "Enable Vertex AI Feature Store"
  type        = bool
  default     = false
}

variable "enable_metadata_store" {
  description = "Enable Vertex AI Metadata Store"
  type        = bool
  default     = false
}

variable "enable_tensorboard" {
  description = "Enable Vertex AI Tensorboard"
  type        = bool
  default     = false
}

variable "create_endpoint" {
  description = "Create Vertex AI endpoints"
  type        = bool
  default     = false
}

variable "enable_dataset" {
  description = "Create Vertex AI dataset"
  type        = bool
  default     = false
}

variable "vpc_network" {
  description = "VPC network for private endpoints"
  type        = string
  default     = null
}

# =============================================================================
# Resource Limits (Cost-Optimized Defaults)
# =============================================================================

variable "feature_store_node_count" {
  description = "Fixed node count for Feature Store online serving (minimum for cost)"
  type        = number
  default     = 1
}

variable "endpoint_min_replicas" {
  description = "Minimum replicas for Vertex AI endpoints"
  type        = number
  default     = 0
}

variable "endpoint_max_replicas" {
  description = "Maximum replicas for Vertex AI endpoints (set low for cost control)"
  type        = number
  default     = 1
}

