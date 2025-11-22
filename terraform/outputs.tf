# Project Outputs
output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

# Network Outputs
output "network_name" {
  description = "The name of the VPC network"
  value       = module.network.network_name
}

output "network_id" {
  description = "The ID of the VPC network"
  value       = module.network.network_id
}

output "vpc_connector_name" {
  description = "The name of the VPC connector for Cloud Run"
  value       = module.network.vpc_connector_name
}

# Database Outputs
output "database_instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = module.database.instance_name
}

output "database_connection_name" {
  description = "The connection name of the Cloud SQL instance"
  value       = module.database.connection_name
}

output "database_private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = module.database.private_ip_address
  sensitive   = true
}

output "database_url" {
  description = "The database connection URL"
  value       = module.database.database_url
  sensitive   = true
}

# Storage Outputs
output "minutes_bucket_name" {
  description = "The name of the GCS bucket for scraped minutes"
  value       = module.storage.minutes_bucket_name
}

output "backups_bucket_name" {
  description = "The name of the GCS bucket for backups"
  value       = module.storage.backups_bucket_name
}

output "exports_bucket_name" {
  description = "The name of the GCS bucket for exports"
  value       = module.storage.exports_bucket_name
}

# Security Outputs
output "google_api_key_secret_id" {
  description = "The ID of the Google API Key secret"
  value       = module.security.google_api_key_secret_id
}

output "cloud_run_service_account_email" {
  description = "The email of the Cloud Run service account"
  value       = module.security.cloud_run_service_account_email
}

# App Outputs
output "streamlit_url" {
  description = "The URL of the Streamlit UI service"
  value       = module.app.streamlit_url
}

output "monitoring_url" {
  description = "The URL of the monitoring dashboard service"
  value       = module.app.monitoring_url
}

output "scraper_worker_url" {
  description = "The URL of the scraper worker service"
  value       = module.app.scraper_worker_url
}

output "processor_worker_url" {
  description = "The URL of the processor worker service"
  value       = module.app.processor_worker_url
}

output "matcher_worker_url" {
  description = "The URL of the matcher worker service"
  value       = module.app.matcher_worker_url
}

# Monitoring Outputs
output "monitoring_dashboard_id" {
  description = "ID of the Cloud Monitoring dashboard"
  value       = module.monitoring.dashboard_id
}

output "uptime_check_id" {
  description = "ID of the uptime check"
  value       = module.monitoring.uptime_check_id
}

output "alert_policy_ids" {
  description = "Map of alert policy names to their IDs"
  value       = module.monitoring.alert_policy_ids
}

# Summary Output
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = {
    project_id         = var.project_id
    region             = var.region
    environment        = var.environment
    network_name       = module.network.network_name
    database_name      = module.database.instance_name
    streamlit_url      = module.app.streamlit_url
    monitoring_dashboard_id = module.monitoring.dashboard_id
  }
}
