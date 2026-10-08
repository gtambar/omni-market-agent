variable "gcp_project_id" {
  description = "Google Cloud Project ID hosting OmniMarket Agent"
  type        = string
}

variable "gcp_region" {
  description = "Google Cloud Region for Cloud Run and Cloud Scheduler"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run v2 service name"
  type        = string
  default     = "omni-market-agent"
}

variable "container_image" {
  description = "Artifact Registry container image URI"
  type        = string
  default     = "us-central1-docker.pkg.dev/project/omni-market/omni-market-agent:latest"
}
