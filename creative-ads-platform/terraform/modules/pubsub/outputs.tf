# Pub/Sub Module - Outputs

output "jobs_topic_name" {
  description = "Jobs topic name"
  value       = google_pubsub_topic.jobs.name
}

output "jobs_topic_id" {
  description = "Jobs topic ID"
  value       = google_pubsub_topic.jobs.id
}

output "jobs_subscription_name" {
  description = "Jobs subscription name"
  value       = google_pubsub_subscription.jobs.name
}

output "dlq_topic_name" {
  description = "DLQ topic name"
  value       = google_pubsub_topic.dlq.name
}

output "dlq_subscription_name" {
  description = "DLQ subscription name"
  value       = google_pubsub_subscription.dlq.name
}

output "feature_extraction_topic_name" {
  description = "Feature extraction topic name"
  value       = google_pubsub_topic.feature_extraction.name
}

output "prompt_generation_topic_name" {
  description = "Prompt generation topic name"
  value       = google_pubsub_topic.prompt_generation.name
}

