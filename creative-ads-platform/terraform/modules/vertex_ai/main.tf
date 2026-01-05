# Vertex AI Module - Main Configuration

# =============================================================================
# Feature Store (Optional - for ML feature management)
# =============================================================================

resource "google_vertex_ai_featurestore" "creative_ads" {
  count = var.enable_feature_store ? 1 : 0

  name   = "creative_ads_features"
  region = var.region

  labels = var.labels

  # Cost-optimized: use minimum node count
  online_serving_config {
    fixed_node_count = var.feature_store_node_count
  }

  force_destroy = var.environment != "production"
}

# =============================================================================
# Feature Store Entity Type (for creative assets)
# =============================================================================

resource "google_vertex_ai_featurestore_entitytype" "creative_asset" {
  count = var.enable_feature_store ? 1 : 0

  name         = "creative_asset"
  featurestore = google_vertex_ai_featurestore.creative_ads[0].id

  labels = var.labels

  monitoring_config {
    snapshot_analysis {
      disabled = false
    }
  }
}

# =============================================================================
# Metadata Store (for ML experiment tracking)
# =============================================================================

# Note: google_vertex_ai_metadata_store requires google-beta provider >= 5.x
# and may need to be enabled via google-beta provider in the module
# Uncomment when using compatible provider version
#
# resource "google_vertex_ai_metadata_store" "default" {
#   provider = google-beta
#   count    = var.enable_metadata_store ? 1 : 0
#
#   name        = "creative-ads-metadata"
#   description = "Metadata store for creative ads ML experiments"
#   region      = var.region
# }

# =============================================================================
# Tensorboard (for training visualization)
# =============================================================================

resource "google_vertex_ai_tensorboard" "creative_ads" {
  count = var.enable_tensorboard ? 1 : 0

  display_name = "creative-ads-tensorboard"
  description  = "Tensorboard for creative ads model training"
  region       = var.region

  labels = var.labels
}

# =============================================================================
# Endpoints (for model serving)
# Note: Actual model deployment is done via CI/CD
# =============================================================================

resource "google_vertex_ai_endpoint" "reverse_prompting" {
  count = var.create_endpoint ? 1 : 0

  name         = "reverse-prompting-endpoint"
  display_name = "Reverse Prompting Endpoint"
  description  = "Endpoint for reverse prompt generation"
  location     = var.region

  labels = var.labels

  # Network configuration for VPC peering if needed
  # network = var.vpc_network
}

resource "google_vertex_ai_endpoint" "feature_extraction" {
  count = var.create_endpoint ? 1 : 0

  name         = "feature-extraction-endpoint"
  display_name = "Feature Extraction Endpoint"
  description  = "Endpoint for visual feature extraction"
  location     = var.region

  labels = var.labels
}

# =============================================================================
# Dataset for training data
# =============================================================================

resource "google_vertex_ai_dataset" "creative_ads" {
  count = var.enable_dataset ? 1 : 0

  display_name        = "creative-ads-dataset"
  metadata_schema_uri = "gs://google-cloud-aiplatform/schema/dataset/metadata/image_1.0.0.yaml"
  region              = var.region

  labels = var.labels
}

# =============================================================================
# IAM for service account
# =============================================================================

# Allow service account to access Vertex AI resources
data "google_project" "current" {}

resource "google_project_iam_member" "vertex_ai_user" {
  project = data.google_project.current.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${var.service_account}"
}

resource "google_project_iam_member" "vertex_ai_admin" {
  count = var.environment != "production" ? 1 : 0

  project = data.google_project.current.project_id
  role    = "roles/aiplatform.admin"
  member  = "serviceAccount:${var.service_account}"
}

