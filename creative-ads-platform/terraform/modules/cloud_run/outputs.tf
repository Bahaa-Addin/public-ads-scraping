# Cloud Run Module - Outputs

output "agent_url" {
  description = "Agent service URL"
  value       = google_cloud_run_v2_service.agent.uri
}

output "agent_service_name" {
  description = "Agent service name"
  value       = google_cloud_run_v2_service.agent.name
}

output "scraper_url" {
  description = "Scraper service URL"
  value       = google_cloud_run_v2_service.scraper.uri
}

output "scraper_service_name" {
  description = "Scraper service name"
  value       = google_cloud_run_v2_service.scraper.name
}

