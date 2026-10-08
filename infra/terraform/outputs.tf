output "cloud_run_service_url" {
  description = "HTTPS URL of the deployed 24/7 OmniMarket Agent service"
  value       = google_cloud_run_v2_service.omni_market_agent.uri
}

output "service_account_email" {
  description = "Dedicated least-privilege service account email"
  value       = google_service_account.omni_market_agent_sa.email
}

output "scheduler_job_name" {
  description = "3-minute 24/7 Cloud Scheduler job name"
  value       = google_cloud_scheduler_job.refresh_every_3_minutes.name
}
