# Grafana監視システムセットアップガイド

> **設計判断の背景**: [ADR 0016: 監視・メトリクス統合戦略](../ADR/0016-monitoring-metrics-integration.md) を参照

## 概要

Polibaseの監視システムは、Grafana、Prometheus、Lokiを使用してメトリクスとログを統合的に可視化します。

## アーキテクチャ

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Polibase   │────▶│ Prometheus  │────▶│   Grafana   │
│    App      │     │  (Metrics)  │     │ (Dashboard) │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                         ▲
       │            ┌─────────────┐              │
       └───────────▶│    Loki     │──────────────┘
                    │   (Logs)    │
                    └─────────────┘
```

## セットアップ手順

### 1. 監視インフラの起動

```bash
# 監視サービスを起動
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml up -d

# サービスの確認
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml ps
```

### 2. Grafanaへのアクセス

1. ブラウザで http://localhost:3000 にアクセス
2. 初回ログイン
   - Username: `admin`
   - Password: `admin`
3. パスワード変更を促されたら、新しいパスワードを設定

### 3. ダッシュボードの確認

以下のダッシュボードが自動的にプロビジョニングされます：

- **システム概要**: 稼働状況、エラー率、処理数の概要
- **パフォーマンス**: API応答時間、DB性能、LLM使用状況
- **エラー追跡**: エラー率の推移、タイプ別分析
- **ビジネスメトリクス**: 議事録処理統計、データ品質

## 主要なメトリクス

### システムメトリクス
- `up`: サービスの稼働状況
- `http_request_duration_seconds`: HTTPリクエストの処理時間
- `http_requests_total`: HTTPリクエストの総数

### 議事録処理メトリクス
- `minutes_processed_total`: 処理された議事録の総数
- `minutes_processing_duration_seconds`: 議事録処理時間
- `minutes_processing_errors_total`: 議事録処理エラー数

### LLMメトリクス
- `llm_api_calls_total`: LLM API呼び出し総数
- `llm_api_duration_seconds`: LLM API呼び出し時間
- `llm_tokens_used_total`: 使用したトークン数

### データベースメトリクス
- `db_operations_total`: データベース操作の総数
- `db_operation_duration_seconds`: データベース操作の実行時間
- `db_connections_active`: アクティブなDB接続数

## アラート設定

### SLO（Service Level Objectives）

1. **可用性**: > 99.5%
2. **P95レスポンスタイム**: < 2秒
3. **エラー率**: < 1%

### 主要なアラート

| アラート名 | 条件 | 重要度 |
|-----------|------|--------|
| PolibaseServiceDown | サービス停止2分以上 | Critical |
| HighErrorRate | エラー率 > 1% | Warning |
| VeryHighErrorRate | エラー率 > 5% | Critical |
| SlowResponseTime | P95 > 2秒 | Warning |
| HighLLMTokenUsage | 1時間で100万トークン超過 | Warning |

## ログの検索

Grafanaの「Explore」セクションからLokiデータソースを選択して、ログを検索できます。

### よく使うクエリ例

```logql
# エラーログの検索
{job="polibase"} |= "ERROR"

# 特定のサービスのログ
{service="minutes_processor"}

# レスポンスタイムが遅いリクエスト
{job="polibase"} |= "slow_request" |> 1000

# 特定の時間範囲のエラー
{job="polibase"} |= "ERROR" | json | timestamp > "2024-01-01T00:00:00Z"
```

## バックアップとリストア

### Grafanaダッシュボードのバックアップ

```bash
# ダッシュボードのエクスポート
curl -u admin:password http://localhost:3000/api/dashboards/uid/polibase-system-overview \
  > dashboard-backup.json

# ダッシュボードのインポート
curl -u admin:password -X POST \
  -H "Content-Type: application/json" \
  -d @dashboard-backup.json \
  http://localhost:3000/api/dashboards/db
```

### Prometheusデータのバックアップ

```bash
# Prometheusデータのスナップショット作成
curl -X POST http://localhost:9091/api/v1/admin/tsdb/snapshot

# データボリュームのバックアップ
docker run --rm -v docker_prometheus_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/prometheus-backup.tar.gz /data
```

## トラブルシューティング

### Grafanaにログインできない場合

```bash
# パスワードリセット
docker compose exec grafana grafana-cli admin reset-admin-password newpassword
```

### メトリクスが表示されない場合

1. Prometheusのターゲット確認: http://localhost:9091/targets
2. アプリケーションのメトリクスエンドポイント確認: http://localhost:9090/metrics

### ログが表示されない場合

1. Promtailのステータス確認: http://localhost:9080/targets
2. Lokiのログ確認:
   ```bash
   docker compose logs loki
   ```

## カスタマイズ

### 新しいダッシュボードの追加

1. Grafanaで新しいダッシュボードを作成
2. ダッシュボードを保存
3. JSONをエクスポートして `docker/monitoring/grafana/dashboards/` に保存

### アラートルールの追加

`docker/monitoring/prometheus/alerts/polibase-alerts.yml` に新しいルールを追加：

```yaml
- alert: CustomAlert
  expr: your_metric > threshold
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "カスタムアラート"
    description: "詳細な説明"
```

## セキュリティ設定

### Grafanaの認証強化

1. 環境変数でGoogle OAuth設定：
   ```yaml
   environment:
     - GF_AUTH_GOOGLE_ENABLED=true
     - GF_AUTH_GOOGLE_CLIENT_ID=your-client-id
     - GF_AUTH_GOOGLE_CLIENT_SECRET=your-client-secret
   ```

2. チーム同期の設定
3. ロールベースのアクセス制御

### HTTPSの設定

リバースプロキシ（nginx）を使用してHTTPSを設定することを推奨します。

## 参考リンク

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [OpenTelemetry Metrics Guide](opentelemetry_metrics.md)
