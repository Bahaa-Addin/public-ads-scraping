# =============================================================================
# Agentic Ads Dashboard - Terraform Outputs
# =============================================================================

output "dashboard_url" {
  description = "URL of the dashboard frontend"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "api_url" {
  description = "URL of the dashboard API"
  value       = google_cloud_run_v2_service.api.uri
}

output "service_account_email" {
  description = "Email of the dashboard service account"
  value       = google_service_account.dashboard.email
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository for dashboard images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.dashboard.repository_id}"
}

output "api_service_name" {
  description = "Name of the API Cloud Run service"
  value       = google_cloud_run_v2_service.api.name
}

output "frontend_service_name" {
  description = "Name of the frontend Cloud Run service"
  value       = google_cloud_run_v2_service.frontend.name
}

output "monitoring_dashboard_name" {
  description = "Name of the Cloud Monitoring dashboard"
  value       = google_monitoring_dashboard.dashboard.dashboard_json
}

# Computed URLs for integration
output "integration_config" {
  description = "Configuration for integrating with other services"
  value = {
    dashboard_url = google_cloud_run_v2_service.frontend.uri
    api_url       = google_cloud_run_v2_service.api.uri
    health_check  = "${google_cloud_run_v2_service.api.uri}/health"
    metrics       = "${google_cloud_run_v2_service.api.uri}/metrics"
  }
}

