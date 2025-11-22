output "dashboard_id" {
  description = "ID of the monitoring dashboard"
  value       = google_monitoring_dashboard.sagebase_dashboard.id
}

output "uptime_check_id" {
  description = "ID of the uptime check"
  value       = google_monitoring_uptime_check_config.streamlit_ui.uptime_check_id
}

output "alert_policy_ids" {
  description = "Map of alert policy names to their IDs"
  value = {
    service_availability          = google_monitoring_alert_policy.service_availability.id
    high_error_rate              = google_monitoring_alert_policy.high_error_rate.id
    high_response_time           = google_monitoring_alert_policy.high_response_time.id
    high_cpu_usage               = google_monitoring_alert_policy.high_cpu_usage.id
    high_memory_usage            = google_monitoring_alert_policy.high_memory_usage.id
    database_connection_failures = google_monitoring_alert_policy.database_connection_failures.id
  }
}
