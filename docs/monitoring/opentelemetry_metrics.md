# OpenTelemetryメトリクス運用ガイド

> **設計判断の背景**: [ADR 0016: 監視・メトリクス統合戦略](../ADR/0016-monitoring-metrics-integration.md) を参照

## 概要

Polibaseでは、OpenTelemetryを使用してアプリケーションのパフォーマンスメトリクスを収集しています。このドキュメントでは、メトリクスの設定、収集、モニタリング方法について説明します。

## メトリクスの種類

### 1. HTTPメトリクス
- `http_requests_total`: HTTPリクエストの総数
- `http_request_duration_seconds`: HTTPリクエストの処理時間
- `http_requests_in_progress`: 処理中のHTTPリクエスト数

### 2. データベースメトリクス
- `db_operations_total`: データベース操作の総数
- `db_operation_duration_seconds`: データベース操作の実行時間
- `db_connections_active`: アクティブなDB接続数

### 3. 議事録処理メトリクス
- `minutes_processed_total`: 処理された議事録の総数
- `minutes_processing_duration_seconds`: 議事録処理時間
- `minutes_processing_errors_total`: 議事録処理エラー数

### 4. LLMメトリクス
- `llm_api_calls_total`: LLM API呼び出し総数
- `llm_api_duration_seconds`: LLM API呼び出し時間
- `llm_tokens_used_total`: 使用したトークン数

## セットアップ

### 1. 基本設定

```python
from src.common.metrics import setup_metrics

# アプリケーション起動時に実行
setup_metrics(
    service_name="polibase",
    service_version="1.0.0",
    prometheus_port=9090,
    enable_prometheus=True,
)
```

### 2. 環境変数

メトリクス機能は以下の環境変数で制御できます：

```bash
# Prometheusエクスポーターのポート（デフォルト: 9090）
PROMETHEUS_PORT=9090

# メトリクス収集の有効/無効（デフォルト: true）
ENABLE_METRICS=true
```

## メトリクスの使用方法

### 1. デコレーターを使った自動計測

```python
from src.common.instrumentation import measure_time, count_calls

@measure_time(
    metric_name="custom_operation",
    log_slow_operations=2.0,  # 2秒以上かかった場合に警告ログ
)
def process_data(data):
    # 処理時間が自動的に計測される
    return result

@count_calls(metric_name="api_endpoint")
def handle_request(request):
    # 呼び出し回数が自動的にカウントされる
    return response
```

### 2. コンテキストマネージャーを使った計測

```python
from src.common.instrumentation import MetricsContext

with MetricsContext(
    operation="batch_processing",
    labels={"batch_size": "1000"},
    record_duration=True,
    record_errors=True,
) as ctx:
    # バッチ処理
    process_batch()

    # 追加のメトリクスを記録
    ctx.add_metric("items_processed", 950)
    ctx.add_metric("items_failed", 50)
```

### 3. 手動でのメトリクス記録

```python
from src.common.metrics import create_counter, create_histogram

# カウンターの作成と使用
error_counter = create_counter(
    "processing_errors_total",
    "Total processing errors",
    "1",
)
error_counter.add(1, attributes={"error_type": "ValidationError"})

# ヒストグラムの作成と使用
latency_histogram = create_histogram(
    "operation_latency_seconds",
    "Operation latency",
    "s",
)
latency_histogram.record(0.156, attributes={"operation": "parse"})
```

## Prometheusとの統合

### 1. メトリクスエンドポイント

メトリクスは以下のエンドポイントで公開されます：
```
http://localhost:9090/metrics
```

### 2. Prometheusの設定

`prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'polibase'
    scrape_interval: 15s
    static_configs:
      - targets: ['sagebase:9090']
```

### 3. メトリクスの確認

```bash
# すべてのメトリクスを表示
curl http://localhost:9090/metrics

# 特定のメトリクスをフィルタ
curl http://localhost:9090/metrics | grep minutes_processed
```

## 既存コードへの適用方法

### 1. LLMサービスの計測

```python
from src.services.llm_factory import LLMServiceFactory

# ファクトリーは自動的に計測ラッパーを適用
factory = LLMServiceFactory()
llm_service = factory.create_advanced(enable_metrics=True)  # デフォルトでTrue
```

### 2. データベースリポジトリの計測

```python
from src.database.instrumented_repository import InstrumentedRepository

# BaseRepositoryの代わりにInstrumentedRepositoryを使用
class ConversationRepository(InstrumentedRepository):
    # すべてのDB操作が自動的に計測される
    pass
```

### 3. Webスクレイピングの計測

```python
from src.common.instrumentation import measure_time

@measure_time(
    metric_name="web_scraping",
    labels={"site": "kaigiroku.net"},
)
async def scrape_minutes(url: str):
    # スクレイピング処理
    pass
```

## モニタリングとアラート

### 1. 重要なメトリクス

以下のメトリクスを監視することを推奨します：

- **エラー率**: `minutes_processing_errors_total` / `minutes_processed_total`
- **レスポンスタイム**: `http_request_duration_seconds` の95パーセンタイル
- **DB接続数**: `db_connections_active` が設定した上限に近い場合
- **LLMコスト**: `llm_tokens_used_total` の増加率

### 2. アラート例（Prometheus）

```yaml
groups:
  - name: polibase_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(minutes_processing_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "高いエラー率を検出"

      - alert: SlowProcessing
        expr: histogram_quantile(0.95, minutes_processing_duration_seconds) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "議事録処理が遅い"
```

## トラブルシューティング

### 1. メトリクスが表示されない

```python
# メトリクスが初期化されているか確認
from src.common.metrics import get_meter
try:
    meter = get_meter()
    print("メトリクスは初期化されています")
except RuntimeError:
    print("setup_metrics()を呼び出してください")
```

### 2. ポートが使用中

```bash
# 使用中のポートを確認
lsof -i :9090

# 別のポートを使用
setup_metrics(prometheus_port=9091)
```

### 3. メトリクスの確認スクリプト

```bash
# 動作確認スクリプトを実行
docker compose exec sagebase uv run python scripts/verify_metrics.py
```

## ベストプラクティス

1. **ラベルの使用**: メトリクスには適切なラベルを付けて、後でフィルタリングできるようにする
2. **カーディナリティ**: ラベルの値が多すぎないように注意（ユーザーIDなどは避ける）
3. **命名規則**: メトリクス名は`<namespace>_<name>_<unit>`の形式を使用
4. **エラー処理**: メトリクス記録でエラーが発生してもアプリケーションは継続するように
5. **パフォーマンス**: メトリクス収集のオーバーヘッドは最小限に保つ

## 参考リンク

- [OpenTelemetry Python Documentation](https://opentelemetry-python.readthedocs.io/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [Grafana Dashboards for Python](https://grafana.com/grafana/dashboards/)
