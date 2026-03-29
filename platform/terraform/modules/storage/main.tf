# Storage Module - Main Configuration

locals {
  raw_bucket_name       = "${var.project_id}-raw-assets-${var.environment}"
  processed_bucket_name = "${var.project_id}-processed-assets-${var.environment}"
}

# =============================================================================
# Raw Assets Bucket
# =============================================================================

resource "google_storage_bucket" "raw_assets" {
  name          = local.raw_bucket_name
  location      = var.region
  project       = var.project_id
  force_destroy = var.environment != "production"
  storage_class = "STANDARD"

  labels = var.labels

  # Versioning for data protection
  versioning {
    enabled = var.environment == "production"
  }

  # Lifecycle rules (configurable for cost optimization)
  lifecycle_rule {
    condition {
      age = var.raw_nearline_age_days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = var.raw_coldline_age_days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  dynamic "lifecycle_rule" {
    for_each = var.raw_delete_age_days > 0 ? [1] : []
    content {
      condition {
        age        = var.raw_delete_age_days
        with_state = "ANY"
      }
      action {
        type = "Delete"
      }
    }
  }

  # CORS configuration for browser access if needed
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  # Uniform bucket-level access
  uniform_bucket_level_access = true
}

# =============================================================================
# Processed Assets Bucket
# =============================================================================

resource "google_storage_bucket" "processed_assets" {
  name          = local.processed_bucket_name
  location      = var.region
  project       = var.project_id
  force_destroy = var.environment != "production"
  storage_class = "STANDARD"

  labels = var.labels

  versioning {
    enabled = var.environment == "production"
  }

  # Lifecycle rules (configurable for cost optimization)
  lifecycle_rule {
    condition {
      age = var.processed_nearline_age_days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  uniform_bucket_level_access = true
}

# =============================================================================
# Temporary Processing Bucket
# =============================================================================

resource "google_storage_bucket" "temp" {
  name          = "${var.project_id}-temp-processing-${var.environment}"
  location      = var.region
  project       = var.project_id
  force_destroy = true
  storage_class = "STANDARD"

  labels = var.labels

  # Auto-delete temp files (configurable)
  lifecycle_rule {
    condition {
      age = var.temp_delete_age_days
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true
}

# =============================================================================
# IAM Bindings
# =============================================================================

resource "google_storage_bucket_iam_member" "raw_admin" {
  bucket = google_storage_bucket.raw_assets.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.service_account}"
}

resource "google_storage_bucket_iam_member" "processed_admin" {
  bucket = google_storage_bucket.processed_assets.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.service_account}"
}

resource "google_storage_bucket_iam_member" "temp_admin" {
  bucket = google_storage_bucket.temp.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.service_account}"
}

