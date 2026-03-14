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

リポジトリ実装には3種類のモデルパターンが混在しています（[ADR 0007](docs/ADR/0007-repository-model-pattern-standardization.md)）。`BaseRepositoryImpl`の一部メソッド（`get_by_ids`, `count`等）は`select(model_class)`を使用するため、**Pydantic/動的モデル系のリポジトリでは正しく動作しません**。該当リポジトリでは、これらのメソッドをraw SQLで**必ずオーバーライド**してください。

**オーバーライド必須メソッド**: `count()`, `get_by_ids()`

| パターン | モデル基盤 | BaseRepositoryImpl互換 | 該当リポジトリ例 |
|---------|-----------|----------------------|----------------|
| SQLAlchemy ORM | `registry.mapped` / `DeclarativeBase` | `select()`が動作する | Speaker, Minutes等 |
| Pydantic | `PydanticBaseModel` | `select()`が**動作しない** | Conference, GoverningBody等 |
| 動的モデル | 動的`__init__` / ランタイム属性 | `select()`が**動作しない** | Politician, ParliamentaryGroup, Meeting等 |

#### 新規リポジトリ作成ルール（ADR 0007）

- **第1選択**: SQLAlchemy ORM（`BaseRepositoryImpl`と完全互換）
- **条件付き許容**: Pydantic（既存Pydanticモデルの拡張時のみ）
- **新規禁止**: 動的モデル（バグの温床、IDE補完が効かない）

#### 変換メソッド方針（ADR 0007）

- 新規リポジトリでは `_to_entity()` のみを使用（`_dict_to_entity()`, `_row_to_entity()` は使用しない）
- 既存リポジトリは段階的に `_to_entity()` に統一予定

**📖 For detailed architecture**: See [.claude/skills/clean-architecture-checker/](.claude/skills/clean-architecture-checker/)

### Visual Diagrams

- [Layer Dependency](docs/diagrams/layer-dependency.mmd)
- [Component Interaction](docs/diagrams/component-interaction.mmd)
- [Minutes Processing Flow](docs/diagrams/data-flow-minutes-processing.mmd)
- [Repository Pattern](docs/diagrams/repository-pattern.mmd)

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

### Architecture Decision Records (ADR)

設計判断の「なぜ」を記録。全ADRは `docs/ADR/` に格納（現在16本: 0001〜0016）。

- ADR作成ルール: `NNNN-kebab-case-title.md`形式、必須セクション（Status, Context, Decision, Consequences）
- **ADR作成時の必須アクション**: 新しいADRを作成したら、`docs/ADR/`に配置し`ls docs/ADR/`で確認できる状態にすること
- **ADR作成トリガー**: 以下に該当する変更を行う場合、ADRの作成を提案すること：
  - 新しいアーキテクチャパターンや設計方針の導入
  - 既存パターンからの意図的な逸脱
  - 新しい外部サービス・ライブラリの採用
  - 複数の選択肢を検討して判断した場合
- 主要ADR（実装時に特に参照すべきもの）:
  - [ADR 0003](docs/ADR/0003-repository-pattern.md): リポジトリパターン + ISessionAdapter
  - [ADR 0005](docs/ADR/0005-extraction-layer-gold-layer-separation.md): Bronze Layer / Gold Layer分離
  - [ADR 0007](docs/ADR/0007-repository-model-pattern-standardization.md): リポジトリモデルパターン標準化
  - [ADR 0010](docs/ADR/0010-application-layer-transaction-management.md): トランザクション管理（flush/commit分離）
  - [ADR 0012](docs/ADR/0012-error-handling-three-layer-exception-hierarchy.md): エラーハンドリング3層例外体系

### Operations & Guides

人間向け運用手順は `docs/guides/` に格納。監視設定は `docs/monitoring/` に格納。

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
- **Worktree作業時**: `Read`/`Write`/`Edit`等のファイル操作は**必ずworktreeのパス**（カレントディレクトリ配下）を使用すること。親リポジトリのパスを参照してはならない

**📖 For detailed conventions**: See [.claude/skills/project-conventions/](.claude/skills/project-conventions/)

## BAML Integration

すべてのLLM構造化出力にBAML（Boundary ML）を使用。Pydantic実装は全廃済み。
BAML定義ファイルは `baml_src/` に格納。詳細は [ADR 0002](docs/ADR/0002-baml-for-llm-outputs.md) 参照。

- **対応機能**: 議事録分割、議員団メンバー抽出、政治家マッチング、役職-人名マッピング
- **ハイブリッドアプローチ**: ルールベース（信頼度0.9以上）→ BAMLマッチング（複雑ケース）
- **📖 SKILL**: [.claude/skills/baml-integration/](.claude/skills/baml-integration/)

## Data Layer Architecture（Bronze Layer / Gold Layer）

LLM抽出結果と確定データを分離する2層アーキテクチャ。詳細は [ADR 0005](docs/ADR/0005-extraction-layer-gold-layer-separation.md) 参照。

- **Bronze Layer**: LLM抽出結果を追記専用（Immutable）で保存
- **Gold Layer**: 確定データ、人間の修正が最優先
- **📖 SKILL**: [.claude/skills/data-layer-architecture/](.claude/skills/data-layer-architecture/)
