# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**IMPORTANT: このプロジェクトでは、すべての説明、コメント、ドキュメントを日本語で記述してください。**

- コードのコメント: 日本語で記述
- Git commitメッセージ: 日本語で記述
- ドキュメント: 日本語で記述
- Claude Codeとのやり取り: 日本語で応答

This project primarily uses Japanese for all documentation, comments, and communication.

## Project Overview

Sagebase is a Political Activity Tracking Application (政治活動追跡アプリケーション) for managing and analyzing Japanese political activities including politician statements, meeting minutes, political promises, and voting records.

### Core Concepts

- **Politician Information**: Scraped from political party websites
- **Speakers & Speeches**: Extracted from meeting minutes
- **Speaker-Politician Matching**: LLM-based matching with hybrid approach
- **Parliamentary Groups**: Voting blocs within conferences
- **Staged Processing**: Multi-step workflows with manual review capability
- **Conference Member Extraction**: Web scraping + LLM extraction using BAML for structured output

## Quick Start

```bash
# First time setup
cp .env.example .env  # Configure GOOGLE_API_KEY
just up               # Start environment

# Run application
just up               # Start all services and launch Streamlit UI
just bi-dashboard     # Launch BI Dashboard

# Development
just test             # Run tests
just format && just lint  # Format and lint code

# Database
just db               # Connect to PostgreSQL
./reset-database.sh   # Reset database
```

**📖 For detailed commands**: See [.claude/skills/sagebase-commands/](.claude/skills/sagebase-commands/)

## Architecture

Sagebase follows **Clean Architecture** principles. **Status: 🟢 100% Complete**

### Layer Overview

```
src/
├── domain/          # Entities, Repository Interfaces, Domain Services (99 files)
├── application/     # Use Cases, DTOs (68 files)
├── infrastructure/  # Repository Implementations, External Services (103 files)
└── interfaces/      # CLI, Web UI (129 files)
```

### Key Principles

- **Dependency Rule**: Dependencies point inward (Domain ← Application ← Infrastructure ← Interfaces)
- **Entity Independence**: Domain entities have no framework dependencies
- **Repository Pattern**: All repositories use async/await with `ISessionAdapter`
- **DTO Usage**: DTOs for layer boundaries

### Repository Model Types（重要）

リポジトリ実装には2種類のモデルパターンが混在しています。`BaseRepositoryImpl`の一部メソッド（`get_by_ids`, `count`等）は`select(model_class)`を使用するため、**Pydantic/動的モデル系のリポジトリでは正しく動作しません**。該当リポジトリでは、これらのメソッドをraw SQLで**必ずオーバーライド**してください。

**オーバーライド必須メソッド**: `count()`, `get_by_ids()`

| パターン | モデル基盤 | BaseRepositoryImpl互換 | 該当リポジトリ例 |
|---------|-----------|----------------------|----------------|
| SQLAlchemy ORM | `registry.mapped` / `DeclarativeBase` | `select()`が動作する | Speaker, Minutes等 |
| Pydantic/動的モデル | `PydanticBaseModel` / 動的`__init__` | `select()`が**動作しない** | Conference, GoverningBody, Politician, ParliamentaryGroup, Meeting |

**📖 For detailed architecture**: See [.claude/skills/clean-architecture-checker/](.claude/skills/clean-architecture-checker/)

### Visual Diagrams

- [Layer Dependency](docs/diagrams/layer-dependency.mmd)
- [Component Interaction](docs/diagrams/component-interaction.mmd)
- [Minutes Processing Flow](docs/diagrams/data-flow-minutes-processing.mmd)
- [Repository Pattern](docs/diagrams/repository-pattern.mmd)

**📖 Full documentation**: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

## Technology Stack

- **LLM**: Google Gemini API (gemini-2.0-flash, gemini-1.5-flash) via LangChain
- **Structured Output**: BAML (Boundary ML) for type-safe LLM outputs
- **Database**: PostgreSQL 15 with SQLAlchemy ORM
- **Package Management**: UV (modern Python package manager)
- **PDF Processing**: pypdfium2
- **Web Scraping**: Playwright, BeautifulSoup4
- **State Management**: LangGraph for complex workflows
- **Testing**: pytest with pytest-asyncio
- **Cloud Storage**: Google Cloud Storage
- **Data Visualization**: Plotly, Folium, Streamlit

## Documentation

### Architecture & Development

**📖 Overview Documents**:
- **[ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)**: Complete system architecture
- **[CLEAN_ARCHITECTURE_MIGRATION.md](docs/architecture/CLEAN_ARCHITECTURE_MIGRATION.md)**: Migration progress
- **[DEVELOPMENT_GUIDE.md](docs/guides/DEVELOPMENT_GUIDE.md)**: Development workflows

**📁 Architecture Decision Records (ADR)** - `docs/ADR/`:
アーキテクチャに関する重要な意思決定の記録を保管

- ADR作成ルール: `NNNN-kebab-case-title.md`形式、必須セクション（Status, Context, Decision, Consequences）
- 既存のADR:
  - [0001-clean-architecture-adoption.md](docs/ADR/0001-clean-architecture-adoption.md): Clean Architecture採用の経緯
  - [0002-baml-for-llm-outputs.md](docs/ADR/0002-baml-for-llm-outputs.md): BAML採用の経緯
  - [0003-repository-pattern.md](docs/ADR/0003-repository-pattern.md): Repository Pattern採用
  - [0004-langgraph-adapter-pattern.md](docs/ADR/0004-langgraph-adapter-pattern.md): LangGraph Adapter Pattern
  - [0005-extraction-layer-gold-layer-separation.md](docs/ADR/0005-extraction-layer-gold-layer-separation.md): 抽出層とGold Layer分離
  - [0006-alembic-migration-unification.md](docs/ADR/0006-alembic-migration-unification.md): Alembic統一マイグレーション

**📁 Layer Guides** - `docs/architecture/`:
Clean Architectureの各層の詳細な実装ガイドを保管（責務、実装例、落とし穴、チェックリスト）

- [DOMAIN_LAYER.md](docs/architecture/DOMAIN_LAYER.md): エンティティ、リポジトリIF、ドメインサービス
- [APPLICATION_LAYER.md](docs/architecture/APPLICATION_LAYER.md): ユースケース、DTO、トランザクション管理
- [INFRASTRUCTURE_LAYER.md](docs/architecture/INFRASTRUCTURE_LAYER.md): リポジトリ実装、外部サービス
- [INTERFACE_LAYER.md](docs/architecture/INTERFACE_LAYER.md): CLI、Streamlit UI、プレゼンター

### Operations
- **[DEPLOYMENT.md](docs/guides/DEPLOYMENT.md)**: Deployment procedures
- **[BI_DASHBOARD.md](docs/guides/BI_DASHBOARD.md)**: BI Dashboard (Plotly Dash) setup and usage
- **[CICD.md](docs/guides/CICD.md)**: CI/CD workflows
- **[OPERATIONS.md](docs/guides/OPERATIONS.md)**: Operations guide
- **[TROUBLESHOOTING.md](docs/guides/TROUBLESHOOTING.md)**: Troubleshooting guide
- **[docs/monitoring/](docs/monitoring/)**: Monitoring setup (Grafana, Prometheus)

## Important Notes

### Critical Requirements
- **API Key Required**: `GOOGLE_API_KEY` must be set in `.env` for Gemini API access
- **Processing Order**: Always run `process-minutes → extract-speakers → update-speakers` in sequence
- **GCS Authentication**: Run `gcloud auth application-default login` before using GCS features

### File Management
- **Intermediate Files**: Always create temporary files in `tmp/` directory (gitignored)
- **Knowledge Base**: Record important decisions in `_docs/` (gitignored, for Claude's memory)
- **NEVER create .md files in docs/ without explicit approval** - docs/の構成は固定されています
- **Implementation plans go to tmp/** - 実装計画は`tmp/implementation_plan_{issue_number}.md`に配置

### Code Quality
- **Pre-commit Hooks**: **NEVER use `--no-verify`** - always fix errors before committing
- **Testing**: External services (LLM, APIs) must be mocked in tests
- **CI/CD**: Create Issues for any skipped tests with `continue-on-error: true`

### Database
- **Master Data**: Governing bodies and conferences are fixed master data
- **Coverage**: All 1,966 Japanese municipalities tracked with organization codes
- **Migrations**: Alembic統一方式（`alembic/versions/`配下のPythonファイル）。詳細は[ADR 0006](docs/ADR/0006-alembic-migration-unification.md)参照
- **新規マイグレーション**: `just migrate-new "description"` でマイグレーションファイルを作成

### Development
- **Docker-first**: All commands run through Docker containers
- **Unified CLI**: `sagebase` command provides single entry point
- **GCS URI Format**: Always use `gs://` format, not HTTPS URLs
- **Issue実装時の受入基準チェック**: Issue解決時は、実装完了前に受入基準（Acceptance Criteria）の全項目を1つずつ照合すること。UI系の要件（プログレスバー、ダイアログ等）は見落としやすいため特に注意

**📖 For detailed conventions**: See [.claude/skills/project-conventions/](.claude/skills/project-conventions/)

## BAML Integration

### Overview
Sagebaseでは、以下の機能にBAML (Boundary ML)を使用しています。BAMLはLLMの構造化出力を型安全に扱うためのドメイン特化言語(DSL)です。

### Key Features
- **型安全性**: Pydanticモデルと完全に互換性のある型定義
- **トークン効率**: 最適化されたプロンプト生成により、従来のPydantic実装よりトークン使用量を削減
- **パース精度**: LLMの出力を確実に構造化データに変換
- **フィーチャーフラグ対応**: 環境変数で実装を切り替え可能

### BAML対応機能

#### 1. 議事録分割処理（Minutes Divider） **BAML専用**
- **BAML定義**: `baml_src/minutes_divider.baml`
- **実装**: `src/infrastructure/external/minutes_divider/baml_minutes_divider.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用

#### 2. 議員団メンバー抽出（Parliamentary Group Member Extraction） **BAML専用**
- **BAML定義**: `baml_src/parliamentary_group_member_extractor.baml`
- **実装**: `src/infrastructure/external/parliamentary_group_member_extractor/baml_extractor.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用

#### 3. 政治家マッチング（Politician Matching） **BAML専用**
- **BAML定義**: `baml_src/politician_matching.baml`
- **実装**: `src/infrastructure/external/politician_matching/baml_politician_matching_service.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用
- **ハイブリッドアプローチ**: ルールベースマッチング（高速パス）+ BAMLマッチング

#### 4. 役職-人名マッピング抽出（Role Name Mapping） **BAML専用**
- **BAML定義**: `baml_src/role_name_mapping.baml`
- **機能**: 議事録の出席者情報から役職（議長、副議長、知事など）と人名の対応を抽出
- **備考**: 出席者セクションの検出と信頼度スコアリングを提供

### Implementation Pattern
- **High-Speed Path**: ルールベースマッチング（完全一致、部分一致）で信頼度0.9以上の場合はLLMをスキップ
- **LLM Matching**: 複雑なケースのみBAMLを使用してマッチング

### トークン削減効果
- **議事録分割**: 約10-15%削減
- **政治家マッチング**: 約10-15%削減（目標）

### Usage in Streamlit
会議体管理画面の「会議体一覧」タブで、会議体を選択して「選択した会議体から議員情報を抽出」ボタンをクリックすると、BAMLを使用してメンバー情報を抽出できます。抽出結果は「抽出結果確認」タブで確認できます。

## Data Layer Architecture（Bronze Layer / Gold Layer）

Sagebaseでは、LLM抽出結果と確定データを分離する**2層アーキテクチャ**を採用しています。

- **Bronze Layer（抽出ログ層）**: LLM抽出結果を追記専用（Immutable）で保存
- **Gold Layer（確定データ層）**: ユーザーに提供する確定データ、人間の修正が最優先

**📖 For detailed architecture**: See [.claude/skills/data-layer-architecture/](.claude/skills/data-layer-architecture/)
