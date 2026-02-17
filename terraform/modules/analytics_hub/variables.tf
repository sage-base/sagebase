variable "project_id" {
  description = "GCPプロジェクトID"
  type        = string
}

variable "location" {
  description = "BigQueryロケーション"
  type        = string
  default     = "asia-northeast1"
}

variable "exchange_id" {
  description = "Analytics Hub Exchange ID"
  type        = string
  default     = "sagebase_exchange"
}

variable "exchange_display_name" {
  description = "Exchange表示名"
  type        = string
  default     = "Sagebase 政治活動データ"
}

variable "exchange_description" {
  description = "Exchange説明"
  type        = string
  default     = "日本の政治活動追跡データを提供します。全1,966地方議会の議事録・発言・議案賛否等のデータを含みます。"
}

variable "listing_id" {
  description = "Analytics Hub Listing ID"
  type        = string
  default     = "sagebase_gold_listing"
}

variable "listing_display_name" {
  description = "Listing表示名"
  type        = string
  default     = "Sagebase Gold Layer - 政治活動データ"
}

variable "listing_description" {
  description = "Listing説明"
  type        = string
  default     = "日本の地方議会・国会の政治活動データ（Gold Layer）。20テーブル: 政治家、政党、選挙、会議体、議事録、発言、議案、賛否記録等。全1,966地方議会対応。"
}

variable "dataset_id" {
  description = "BigQueryデータセットID"
  type        = string
  default     = "sagebase_gold"
}

variable "primary_contact" {
  description = "連絡先メールアドレス"
  type        = string
  default     = ""
}
