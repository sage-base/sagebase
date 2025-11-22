# Cloud Monitoring Module - Dashboards and Alerts

# Uptime Check for Cloud Run Service
resource "google_monitoring_uptime_check_config" "streamlit_ui" {
  display_name = "Streamlit UI Uptime Check - ${var.environment}"
  timeout      = "10s"
  period       = "60s"

  http_check {
    path           = "/_stcore/health"
    port           = 443
    use_ssl        = true
    validate_ssl   = true
    request_method = "GET"
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = var.service_url
    }
  }

  content_matchers {
    content = "ok"
    matcher = "CONTAINS_STRING"
  }
}

# Alert Policy - Service Availability
resource "google_monitoring_alert_policy" "service_availability" {
  display_name = "Sagebase Service Availability - ${var.environment}"
  combiner     = "OR"
  enabled      = var.enable_alerts

  conditions {
    display_name = "Uptime check failed"

    condition_threshold {
      filter          = "resource.type = \"uptime_url\" AND metric.type = \"monitoring.googleapis.com/uptime_check/check_passed\""
      duration        = "300s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_NEXT_OLDER"
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Streamlit UIサービスのUptime checkが失敗しています。サービスが停止しているか、ヘルスエンドポイントが応答していません。"
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s" # 30分
  }
}

# Alert Policy - High Error Rate
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "Sagebase High Error Rate - ${var.environment}"
  combiner     = "OR"
  enabled      = var.enable_alerts

  conditions {
    display_name = "Error rate > 5%"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.label.response_code_class = \"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05 # 5%

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields = [
          "resource.service_name",
          "resource.revision_name"
        ]
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Cloud Runサービスで5xxエラーが5%を超えています。アプリケーションログを確認してエラーの原因を特定してください。"
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "3600s" # 1時間
  }
}

# Alert Policy - High Response Time
resource "google_monitoring_alert_policy" "high_response_time" {
  display_name = "Sagebase High Response Time - ${var.environment}"
  combiner     = "OR"
  enabled      = var.enable_alerts

  conditions {
    display_name = "Response time > 3 seconds"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 3000 # 3秒（ミリ秒）

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
        group_by_fields = [
          "resource.service_name"
        ]
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Cloud Runサービスのレスポンスタイム（95パーセンタイル）が3秒を超えています。パフォーマンス問題を調査してください。"
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "3600s"
  }
}

# Alert Policy - High CPU Usage
resource "google_monitoring_alert_policy" "high_cpu_usage" {
  display_name = "Sagebase High CPU Usage - ${var.environment}"
  combiner     = "OR"
  enabled      = var.enable_alerts

  conditions {
    display_name = "CPU utilization > 80%"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/container/cpu/utilizations\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8 # 80%

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields = [
          "resource.service_name"
        ]
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Cloud RunサービスのCPU使用率が80%を超えています。インスタンス数の増加やCPU割り当ての見直しを検討してください。"
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "3600s"
  }
}

# Alert Policy - High Memory Usage
resource "google_monitoring_alert_policy" "high_memory_usage" {
  display_name = "Sagebase High Memory Usage - ${var.environment}"
  combiner     = "OR"
  enabled      = var.enable_alerts

  conditions {
    display_name = "Memory utilization > 85%"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/container/memory/utilizations\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85 # 85%

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields = [
          "resource.service_name"
        ]
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Cloud Runサービスのメモリ使用率が85%を超えています。メモリリークの可能性があるか、メモリ割り当てを増やす必要があります。"
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "3600s"
  }
}

# Alert Policy - Database Connection Failures
resource "google_monitoring_alert_policy" "database_connection_failures" {
  display_name = "Sagebase Database Connection Failures - ${var.environment}"
  combiner     = "OR"
  enabled      = var.enable_alerts

  conditions {
    display_name = "Cloud SQL connection failures"

    condition_threshold {
      filter          = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/network/connections\""
      duration        = "300s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields = [
          "resource.database_id"
        ]
      }
    }
  }

  notification_channels = var.notification_channels

  documentation {
    content   = "Cloud SQLデータベースへの接続が確立されていません。データベースインスタンスの状態とネットワーク設定を確認してください。"
    mime_type = "text/markdown"
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# Monitoring Dashboard
resource "google_monitoring_dashboard" "sagebase_dashboard" {
  dashboard_json = jsonencode({
    displayName = "Sagebase Monitoring Dashboard - ${var.environment}"
    mosaicLayout = {
      columns = 12
      tiles = [
        # Cloud Run Request Count
        {
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run - Request Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Requests/sec"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud Run Error Rate
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run - Error Rate (5xx)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.label.response_code_class = \"5xx\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Errors/sec"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud Run Response Latency
        {
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run - Response Latency (p50, p95, p99)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_50"
                      }
                    }
                  }
                  plotType      = "LINE"
                  targetAxis    = "Y1"
                  legendTemplate = "p50"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_95"
                      }
                    }
                  }
                  plotType      = "LINE"
                  targetAxis    = "Y1"
                  legendTemplate = "p95"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_99"
                      }
                    }
                  }
                  plotType      = "LINE"
                  targetAxis    = "Y1"
                  legendTemplate = "p99"
                }
              ]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Latency (ms)"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud Run CPU Utilization
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run - CPU Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/container/cpu/utilizations\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "CPU Utilization"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud Run Memory Utilization
        {
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run - Memory Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/container/memory/utilizations\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Memory Utilization"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud Run Instance Count
        {
          xPos   = 6
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run - Instance Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND metric.type = \"run.googleapis.com/container/instance_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Instances"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud SQL Connections
        {
          yPos   = 12
          width  = 6
          height = 4
          widget = {
            title = "Cloud SQL - Active Connections"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/network/connections\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "Connections"
                scale = "LINEAR"
              }
            }
          }
        },
        # Cloud SQL CPU Utilization
        {
          xPos   = 6
          yPos   = 12
          width  = 6
          height = 4
          widget = {
            title = "Cloud SQL - CPU Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloudsql_database\" AND metric.type = \"cloudsql.googleapis.com/database/cpu/utilization\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              timeshiftDuration = "0s"
              yAxis = {
                label = "CPU Utilization"
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}
