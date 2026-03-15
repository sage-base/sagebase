# ADR 0016: 監視・メトリクス統合戦略（OpenTelemetry + Grafana）

## Status

Accepted (2026-03-13)

## Context

### 背景

Polibaseは議事録処理、LLM API呼び出し、Webスクレイピング、データベース操作など、多様な処理を行うアプリケーションです。これらの処理のパフォーマンス監視、エラー検知、コスト管理（特にLLMトークン使用量）を統合的に行う監視戦略が必要でした。

既にLLMサービスには `InstrumentedLLMService` デコレーターパターン（[ADR 0011](0011-llm-service-decorator-pattern.md)）を採用しており、計測・履歴記録の仕組みが組み込まれています。この計測基盤を、アプリケーション全体の監視に拡張する必要がありました。

### 監視対象のメトリクス

以下の4カテゴリのメトリクスを収集する必要があります:

1. **HTTPメトリクス**: リクエスト数（`http_requests_total`）、処理時間（`http_request_duration_seconds`）、処理中リクエスト数（`http_requests_in_progress`）
2. **データベースメトリクス**: DB操作数（`db_operations_total`）、実行時間（`db_operation_duration_seconds`）、アクティブ接続数（`db_connections_active`）
3. **議事録処理メトリクス**: 処理数（`minutes_processed_total`）、処理時間（`minutes_processing_duration_seconds`）、エラー数（`minutes_processing_errors_total`）
4. **LLMメトリクス**: API呼び出し数（`llm_api_calls_total`）、呼び出し時間（`llm_api_duration_seconds`）、トークン使用量（`llm_tokens_used_total`）

### 検討した代替案

#### Option A: Cloud Monitoringのみ

Google Cloud Platform標準のCloud Monitoring / Cloud Loggingのみで監視する方式。

**利点**: GCPとのネイティブ統合、追加インフラ不要、Cloud Run/Cloud SQLのメトリクスが自動収集される
**欠点**: カスタムメトリクス（LLMトークン、議事録処理）の追加に手間がかかる、ローカル開発環境での監視が困難、ダッシュボードのカスタマイズ性が低い、GCPロックインが発生する

#### Option B: カスタムロギングのみ

Pythonの標準ロギング機構を使い、構造化ログにメトリクス情報を含めて出力する方式。

**利点**: 追加依存なし、実装が簡単、ログファイルで確認可能
**欠点**: メトリクスの集約・可視化が困難、時系列データの分析に不向き、アラート設定ができない、パフォーマンスの傾向分析が手動作業になる

## Decision

**OpenTelemetryベースのメトリクス収集 + Grafana / Prometheus / Loki統合ダッシュボード**方式を採用します。

### アーキテクチャ

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

### 実装方式

#### 1. メトリクス収集（OpenTelemetry）

`src/common/metrics.py` で `setup_metrics()` を呼び出し、Prometheusエクスポーターを設定します。メトリクスは `http://localhost:9090/metrics` で公開されます。

```python
setup_metrics(
    service_name="polibase",
    service_version="1.0.0",
    prometheus_port=9090,
    enable_prometheus=True,
)
```

#### 2. 計測のパターン

3つの計測パターンを提供します:

- **デコレーター**: `@measure_time()` / `@count_calls()` でメソッド単位の自動計測
- **コンテキストマネージャー**: `MetricsContext` でブロック単位の計測と追加メトリクス記録
- **手動記録**: `create_counter()` / `create_histogram()` でカスタムメトリクスの手動記録

#### 3. 既存コードとの統合

- **LLMサービス**: `LLMServiceFactory` が自動的に計測ラッパー（`InstrumentedLLMService`、ADR 0011）を適用
- **データベースリポジトリ**: `InstrumentedRepository` を基底クラスとして使用し、全DB操作を自動計測
- **Webスクレイピング**: `@measure_time()` デコレーターで個別に計測

#### 4. 監視インフラ

Docker Composeで監視サービスを起動:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml up -d
```

Grafanaは `http://localhost:3000` でアクセスし、以下のダッシュボードが自動プロビジョニングされます:
- **システム概要**: 稼働状況、エラー率、処理数の概要
- **パフォーマンス**: API応答時間、DB性能、LLM使用状況
- **エラー追跡**: エラー率の推移、タイプ別分析
- **ビジネスメトリクス**: 議事録処理統計、データ品質

### SLOとアラート

| アラート名 | 条件 | 重要度 |
|-----------|------|--------|
| PolibaseServiceDown | サービス停止2分以上 | Critical |
| HighErrorRate | エラー率 > 1% | Warning |
| VeryHighErrorRate | エラー率 > 5% | Critical |
| SlowResponseTime | P95 > 2秒 | Warning |
| HighLLMTokenUsage | 1時間で100万トークン超過 | Warning |

アラートルールは `docker/monitoring/prometheus/alerts/polibase-alerts.yml` で管理されます。

### 環境変数

```bash
PROMETHEUS_PORT=9090       # Prometheusエクスポーターのポート
ENABLE_METRICS=true        # メトリクス収集の有効/無効
```

## Consequences

### 利点

- **統合的な可視化**: Grafanaダッシュボードでメトリクスとログを一元的に確認可能
- **標準準拠**: OpenTelemetryという業界標準に基づくため、将来的なツール変更が容易
- **ローカル・クラウド両対応**: ローカル開発環境でもDocker Composeで同じ監視環境を再現可能、クラウド環境ではCloud Monitoring（Cloud Trace含む）との併用も可能
- **LLMコスト管理**: `llm_tokens_used_total` メトリクスによりLLM API使用量をリアルタイムで監視
- **ADR 0011との整合性**: `InstrumentedLLMService` デコレーターパターンと自然に統合
- **アラート機能**: PrometheusのAlertManagerにより閾値ベースの自動通知が可能

### トレードオフ

- **インフラの複雑さ**: Prometheus、Grafana、Lokiの3サービスを追加で運用する必要がある
- **リソース消費**: 監視サービス自体がCPU/メモリを消費する
- **学習コスト**: PromQL、LogQL、Grafanaダッシュボード構築の知識が必要
- **メトリクスのカーディナリティ管理**: ラベルの値が多すぎるとPrometheusのパフォーマンスに影響するため、注意が必要（ユーザーIDなどの高カーディナリティラベルは避ける）

## References

- [ADR 0011: LLMサービスのデコレーターパターン](0011-llm-service-decorator-pattern.md) - InstrumentedLLMServiceの設計
- [OpenTelemetryメトリクス運用ガイド](../monitoring/opentelemetry_metrics.md) - セットアップと使用方法の詳細
- [Grafana監視システムセットアップガイド](../monitoring/grafana-setup.md) - Grafana/Prometheus/Lokiの構築手順
- `src/common/metrics.py` - メトリクス設定・ユーティリティ
- `src/common/instrumentation.py` - 計測デコレーター・コンテキストマネージャー
- `docker/docker-compose.monitoring.yml` - 監視インフラのDocker Compose定義
- `docker/monitoring/prometheus/alerts/polibase-alerts.yml` - アラートルール定義
