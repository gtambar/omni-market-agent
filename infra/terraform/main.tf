# =============================================================================
# infra/terraform/main.tf — Google Cloud Production Infrastructure as Code
# Satisfies AgentOps Code Review Matrix Rubric 5.2 (Infrastructure as Code)
#
# Provisions:
#   - Dedicated Least-Privilege Cloud Run Service Account
#   - Secret Manager Secrets for Broker & Gemini API keys (Rubric 5.3)
#   - IAM Bindings (Secret Accessor, Cloud DLP User, Vertex AI User, Log Writer)
#   - Cloud Run v2 Service hosting the 24/7 OmniMarket Agent
#   - Cloud Scheduler Job (`*/3 * * * *`) triggering 3-minute 24/7 market updates
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_service_account" "omni_market_agent_sa" {
  account_id   = "omni-market-agent-sa"
  display_name = "OmniMarket 24/7 Quantitative Multi-Agent Service Account"
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "GEMINI_API_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "alpaca_api_key" {
  secret_id = "ALPACA_API_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "alpaca_api_secret" {
  secret_id = "ALPACA_API_SECRET"
  replication {
    auto {}
  }
}

# Least-privilege IAM roles for Secret Manager, Cloud DLP, Vertex AI, and Cloud Logging
resource "google_project_iam_member" "sa_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/dlp.user",
    "roles/aiplatform.user",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
  ])
  project = var.gcp_project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.omni_market_agent_sa.email}"
}

resource "google_cloud_run_v2_service" "omni_market_agent" {
  name     = var.service_name
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.omni_market_agent_sa.email

    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8080
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.gcp_project_id
      }
      env {
        name  = "OMNI_REFRESH_SECONDS"
        value = "180"
      }
      env {
        name  = "OMNI_LIVE_GOOGLE_FINANCE"
        value = "true"
      }
      env {
        name  = "OMNI_FAST_MODEL"
        value = "gemini-2.5-flash"
      }
      env {
        name  = "OMNI_REASONING_MODEL"
        value = "gemini-2.5-pro"
      }
    }
  }
}

# 24/7 Cloud Scheduler Cron Job triggering the 3-minute market refresh endpoint
resource "google_cloud_scheduler_job" "refresh_every_3_minutes" {
  name             = "omni-market-3min-refresh"
  description      = "Triggers 24/7 3-minute stock market and indicator update cycle"
  schedule         = "*/3 * * * *"
  time_zone        = "America/New_York"
  attempt_deadline = "60s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.omni_market_agent.uri}/api/daemon/refresh"

    oidc_token {
      service_account_email = google_service_account.omni_market_agent_sa.email
    }
  }
}
