# Project Configuration
variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "asia-northeast1" # Tokyo
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

# Network Configuration
variable "network_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "sagebase-vpc"
}

# Database Configuration
variable "database_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "database_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro" # Default to small instance for development

  validation {
    condition     = can(regex("^db-(f1-micro|g1-small|custom-[0-9]+-[0-9]+)$", var.database_tier))
    error_message = "Database tier must be a valid Cloud SQL tier (e.g., db-f1-micro, db-g1-small, db-custom-2-8192)."
  }
}

variable "database_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "sagebase_db"
}

variable "database_user" {
  description = "PostgreSQL database user"
  type        = string
  default     = "sagebase_user"
}

variable "database_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

variable "enable_high_availability" {
  description = "Enable high availability for Cloud SQL (not available for f1-micro)"
  type        = bool
  default     = false
}

variable "enable_backup" {
  description = "Enable automated backups for Cloud SQL"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

# Secrets Configuration
variable "google_api_key" {
  description = "Google API Key (Gemini)"
  type        = string
  sensitive   = true
}

variable "sentry_dsn" {
  description = "Sentry DSN for error tracking"
  type        = string
  sensitive   = true
  default     = ""
}

# Container Image Configuration
variable "streamlit_image" {
  description = "Docker image for Streamlit UI service"
  type        = string
  default     = "gcr.io/PROJECT_ID/streamlit-ui:latest"
}

variable "monitoring_image" {
  description = "Docker image for monitoring dashboard service"
  type        = string
  default     = "gcr.io/PROJECT_ID/monitoring-dashboard:latest"
}

variable "scraper_image" {
  description = "Docker image for scraper worker"
  type        = string
  default     = "gcr.io/PROJECT_ID/scraper-worker:latest"
}

variable "processor_image" {
  description = "Docker image for processor worker"
  type        = string
  default     = "gcr.io/PROJECT_ID/processor-worker:latest"
}

variable "matcher_image" {
  description = "Docker image for matcher worker"
  type        = string
  default     = "gcr.io/PROJECT_ID/matcher-worker:latest"
}

# Analytics Hub Configuration
variable "analytics_hub_primary_contact" {
  description = "Analytics Hub の連絡先メールアドレス"
  type        = string
  default     = ""
}

# Tags
variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    project    = "polibase"
    managed_by = "terraform"
  }
}
