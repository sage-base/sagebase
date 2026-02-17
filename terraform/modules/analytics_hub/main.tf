# Analytics Hub Exchange
resource "google_bigquery_analytics_hub_data_exchange" "sagebase" {
  location         = var.location
  data_exchange_id = var.exchange_id
  display_name     = var.exchange_display_name
  description      = var.exchange_description
  primary_contact  = var.primary_contact
  discovery_type   = "DISCOVERY_TYPE_PUBLIC"
}

# Analytics Hub Listing（sagebase_gold データセットを紐付け）
resource "google_bigquery_analytics_hub_listing" "sagebase_gold" {
  location         = var.location
  data_exchange_id = google_bigquery_analytics_hub_data_exchange.sagebase.data_exchange_id
  listing_id       = var.listing_id
  display_name     = var.listing_display_name
  description      = var.listing_description

  bigquery_dataset {
    dataset = "projects/${var.project_id}/datasets/${var.dataset_id}"
  }

  data_provider {
    name            = "Sagebase"
    primary_contact = var.primary_contact
  }

  publisher {
    name            = "Sagebase Project"
    primary_contact = var.primary_contact
  }
}

# Exchange への公開アクセス設定（全ユーザーが閲覧可能）
resource "google_bigquery_analytics_hub_data_exchange_iam_member" "public_viewer" {
  location         = var.location
  data_exchange_id = google_bigquery_analytics_hub_data_exchange.sagebase.data_exchange_id
  role             = "roles/analyticshub.viewer"
  member           = "allAuthenticatedUsers"
}

# Exchange への公開サブスクライブ設定（全ユーザーがサブスクライブ可能）
resource "google_bigquery_analytics_hub_data_exchange_iam_member" "public_subscriber" {
  location         = var.location
  data_exchange_id = google_bigquery_analytics_hub_data_exchange.sagebase.data_exchange_id
  role             = "roles/analyticshub.subscriber"
  member           = "allAuthenticatedUsers"
}
