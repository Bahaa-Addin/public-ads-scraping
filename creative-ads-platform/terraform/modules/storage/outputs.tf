# Storage Module - Outputs

output "raw_bucket_name" {
  description = "Raw assets bucket name"
  value       = google_storage_bucket.raw_assets.name
}

output "raw_bucket_url" {
  description = "Raw assets bucket URL"
  value       = google_storage_bucket.raw_assets.url
}

output "processed_bucket_name" {
  description = "Processed assets bucket name"
  value       = google_storage_bucket.processed_assets.name
}

output "processed_bucket_url" {
  description = "Processed assets bucket URL"
  value       = google_storage_bucket.processed_assets.url
}

output "temp_bucket_name" {
  description = "Temp processing bucket name"
  value       = google_storage_bucket.temp.name
}

