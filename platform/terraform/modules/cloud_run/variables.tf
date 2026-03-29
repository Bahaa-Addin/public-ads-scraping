# Cloud Run Module - Variables

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

# Container images
variable "agent_image" {
  description = "Docker image for agent service"
  type        = string
}

variable "scraper_image" {
  description = "Docker image for scraper service"
  type        = string
}

# Environment configuration
variable "pubsub_topic" {
  description = "Pub/Sub topic name"
  type        = string
}

variable "pubsub_subscription" {
  description = "Pub/Sub subscription name"
  type        = string
}

variable "raw_bucket" {
  description = "Raw assets bucket name"
  type        = string
}

variable "processed_bucket" {
  description = "Processed assets bucket name"
  type        = string
}

# Scaling configuration (Cost-Optimized Defaults)
variable "agent_min_instances" {
  description = "Minimum agent instances"
  type        = number
  default     = 0
}

variable "agent_max_instances" {
  description = "Maximum agent instances (set low for cost control)"
  type        = number
  default     = 1
}

variable "scraper_min_instances" {
  description = "Minimum scraper instances"
  type        = number
  default     = 0
}

variable "scraper_max_instances" {
  description = "Maximum scraper instances (set low for cost control)"
  type        = number
  default     = 1
}

# Resource limits (Cost-Optimized Defaults)
variable "agent_cpu" {
  description = "CPU for agent service"
  type        = string
  default     = "0.25"
}

variable "agent_memory" {
  description = "Memory for agent service"
  type        = string
  default     = "512Mi"
}

variable "scraper_cpu" {
  description = "CPU for scraper service"
  type        = string
  default     = "0.25"
}

variable "scraper_memory" {
  description = "Memory for scraper service"
  type        = string
  default     = "512Mi"
}

# Network
variable "vpc_connector" {
  description = "VPC connector name"
  type        = string
  default     = null
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access"
  type        = bool
  default     = false
}

