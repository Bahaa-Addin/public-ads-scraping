# Storage Module - Variables

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

# =============================================================================
# Lifecycle Configuration (Cost-Optimized for Testing)
# =============================================================================

variable "raw_nearline_age_days" {
  description = "Days before moving raw assets to nearline storage"
  type        = number
  default     = 7 # Short for testing (prod: 90)
}

variable "raw_coldline_age_days" {
  description = "Days before moving raw assets to coldline storage"
  type        = number
  default     = 30 # Short for testing (prod: 365)
}

variable "raw_delete_age_days" {
  description = "Days before deleting raw assets (0 = never delete)"
  type        = number
  default     = 60 # Short for testing (prod: 730)
}

variable "processed_nearline_age_days" {
  description = "Days before moving processed assets to nearline storage"
  type        = number
  default     = 14 # Short for testing (prod: 180)
}

variable "temp_delete_age_days" {
  description = "Days before deleting temp files"
  type        = number
  default     = 1
}

