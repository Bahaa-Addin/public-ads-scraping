# Vertex AI Module - Outputs

output "endpoint_id" {
  description = "Reverse prompting endpoint ID"
  value       = var.create_endpoint ? google_vertex_ai_endpoint.reverse_prompting[0].id : null
}

output "model_id" {
  description = "Model ID (placeholder - models are deployed via CI/CD)"
  value       = "gemini-1.5-pro"
}

output "feature_store_id" {
  description = "Feature store ID"
  value       = var.enable_feature_store ? google_vertex_ai_featurestore.creative_ads[0].id : null
}

output "tensorboard_id" {
  description = "Tensorboard ID"
  value       = var.enable_tensorboard ? google_vertex_ai_tensorboard.creative_ads[0].id : null
}

output "dataset_id" {
  description = "Dataset ID"
  value       = var.enable_dataset ? google_vertex_ai_dataset.creative_ads[0].id : null
}

