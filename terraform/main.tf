terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  # Backend configuration for storing Terraform state
  # Uncomment and configure for production use
  # backend "gcs" {
  #   bucket = "sagebase-terraform-state"
  #   prefix = "terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required Google Cloud APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",           # Compute Engine API
    "servicenetworking.googleapis.com", # Service Networking API (for VPC peering)
    "sqladmin.googleapis.com",          # Cloud SQL Admin API
    "run.googleapis.com",               # Cloud Run API
    "secretmanager.googleapis.com",     # Secret Manager API
    "storage-api.googleapis.com",       # Google Cloud Storage API
    "iam.googleapis.com",               # Identity and Access Management API
    "logging.googleapis.com",           # Cloud Logging API
    "monitoring.googleapis.com",        # Cloud Monitoring API
    "cloudtrace.googleapis.com",        # Cloud Trace API
    "aiplatform.googleapis.com",        # Vertex AI API
  ])

  service            = each.key
  disable_on_destroy = false
}

# Network Module - VPC and Networking
module "network" {
  source = "./modules/network"

  project_id   = var.project_id
  region       = var.region
  environment  = var.environment
  network_name = var.network_name

  depends_on = [google_project_service.required_apis]
}

# Storage Module - GCS Buckets
module "storage" {
  source = "./modules/storage"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  depends_on = [google_project_service.required_apis]
}

# Security Module - Secret Manager and IAM
module "security" {
  source = "./modules/security"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  # Secrets configuration
  google_api_key    = var.google_api_key
  database_password = var.database_password
  sentry_dsn        = var.sentry_dsn

  depends_on = [google_project_service.required_apis]
}

# Database Module - Cloud SQL PostgreSQL
module "database" {
  source = "./modules/database"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  # Network configuration
  network_id             = module.network.network_id
  private_vpc_connection = module.network.private_vpc_connection

  # Database configuration
  database_version  = var.database_version
  database_tier     = var.database_tier
  database_name     = var.database_name
  database_user     = var.database_user
  database_password = var.database_password

  # High availability
  enable_high_availability = var.enable_high_availability
  enable_backup            = var.enable_backup
  backup_retention_days    = var.backup_retention_days

  depends_on = [module.network, google_project_service.required_apis]
}

# App Module - Cloud Run Services
module "app" {
  source = "./modules/app"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  # Network configuration
  vpc_connector_name = module.network.vpc_connector_name

  # Service account
  service_account_email = module.security.cloud_run_service_account_email

  # Database connection
  database_connection_name = module.database.connection_name
  database_url             = module.database.database_url

  # Secret references
  google_api_key_secret = module.security.google_api_key_secret_id
  sentry_dsn_secret     = module.security.sentry_dsn_secret_id

  # GCS bucket names
  minutes_bucket = module.storage.minutes_bucket_name
  backups_bucket = module.storage.backups_bucket_name
  exports_bucket = module.storage.exports_bucket_name

  # Container image configuration
  streamlit_image  = var.streamlit_image
  monitoring_image = var.monitoring_image
  scraper_image    = var.scraper_image
  processor_image  = var.processor_image
  matcher_image    = var.matcher_image

  depends_on = [
    module.network,
    module.database,
    module.security,
    module.storage,
    google_project_service.required_apis
  ]
}

# Monitoring Module - Cloud Monitoring Dashboards and Alerts
module "monitoring" {
  source = "./modules/monitoring"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment

  # Extract hostname from URL (remove https://)
  service_url = replace(module.app.streamlit_url, "https://", "")

  # Enable alerts for staging and production
  enable_alerts = var.environment != "development"

  # Notification channels (configure via terraform.tfvars)
  notification_channels = []

  depends_on = [
    module.app,
    google_project_service.required_apis
  ]
}
