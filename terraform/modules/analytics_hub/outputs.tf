output "exchange_name" {
  description = "作成されたExchangeのリソース名"
  value       = google_bigquery_analytics_hub_data_exchange.sagebase.name
}

output "exchange_id" {
  description = "Exchange ID"
  value       = google_bigquery_analytics_hub_data_exchange.sagebase.data_exchange_id
}

output "listing_name" {
  description = "作成されたListingのリソース名"
  value       = google_bigquery_analytics_hub_listing.sagebase_gold.name
}

output "listing_id" {
  description = "Listing ID"
  value       = google_bigquery_analytics_hub_listing.sagebase_gold.listing_id
}
