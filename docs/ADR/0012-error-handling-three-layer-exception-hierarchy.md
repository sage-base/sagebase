# ADR 0012: エラーハンドリング3層例外体系

## Status

Accepted (2026-03-13)

## Context

### 背景

Clean Architecture（ADR 0001）を採用した結果、例外処理もアーキテクチャの層境界に沿った設計が必要になりました。Pythonの標準的な例外処理（`try-except Exception`）だけでは、以下の課題がありました：

- **例外の出所が不明**: `Exception`を catch すると、ドメインエラーなのかDBエラーなのか区別できない
- **リトライ判断ができない**: 一時的なAPI障害（リトライ可能）と入力データ不正（リトライ不可）を区別できない
- **層境界の違反**: Infrastructure層の例外（`SQLAlchemyError`）がApplication層やInterface層に漏洩する
- **エラーコードの不在**: 運用時のエラー追跡に一意のコードが必要

### 検討した代替案

#### 1. 標準例外のみ使用

```python
# ❌ ValueError, RuntimeError で済ませる
raise ValueError("政治家が見つかりません")
```

**問題点**: エラーの種類が曖昧。運用時のフィルタリングや自動対応が困難。

#### 2. 単一の例外階層

```python
# ❌ 1つの基底クラスから全例外を派生
class PolibaseError(Exception): ...
class NotFoundError(PolibaseError): ...
class DatabaseError(PolibaseError): ...
```

**問題点**: 層の区別がなく、Infrastructure層の例外をApplication層で直接catchする依存が生まれる。

#### 3. 3層例外体系（選択）

層ごとに独立した例外階層を持ち、層境界で例外を変換する方式。

## Decision

**例外を3層に分離し、エラーコード体系と再試行可能性の判別を組み込む。**

### 例外階層

```
PolibaseException (基底: error_code + message + details)
├── DomainException (DOM-xxx)
│   ├── EntityNotFoundException (DOM-001)
│   ├── BusinessRuleViolationException (DOM-002)
│   ├── InvalidEntityStateException (DOM-003)
│   ├── DuplicateEntityException (DOM-004)
│   ├── InvalidDomainOperationException (DOM-005)
│   ├── DataIntegrityException (DOM-006)
│   ├── ExternalServiceException (DOM-007)
│   ├── RepositoryError (DOM-008)
│   ├── DataValidationException (DOM-009)
│   └── RetryableException (DOM-010) ← 再試行可能な例外の基底
│       ├── RateLimitExceededException (DOM-011)
│       └── TemporaryServiceException (DOM-012)
│
├── ApplicationException (APP-xxx)
│   ├── UseCaseException (APP-001)
│   ├── ValidationException (APP-002)
│   ├── AuthorizationException (APP-003)
│   ├── ResourceNotFoundException (APP-004)
│   ├── WorkflowException (APP-005)
│   ├── ConcurrencyException (APP-006)
│   ├── ConfigurationException (APP-007)
│   ├── DataProcessingException (APP-008)
│   │   ├── PDFProcessingException
│   │   └── TextExtractionException
│   ├── ProcessingException (APP-009)
│   └── AuthenticationFailedException (APP-010)
│
└── InfrastructureException (INFRA-xxx)
    ├── DatabaseError
    └── UpdateError
```

### 設計原則

#### 1. 基底例外クラスの構造化

```python
class PolibaseException(Exception):
    def __init__(self, message: str, error_code: str | None, details: dict | None):
        self.message = message
        self.error_code = error_code   # "DOM-001", "APP-002" 等
        self.details = details or {}   # 追跡用の構造化データ
```

すべての例外がエラーコード（`DOM-001`形式）と構造化された詳細情報を持つ。これにより、ログフィルタリングやアラート設定が容易になる。

#### 2. 再試行可能な例外の分離

```python
class RetryableException(DomainException):
    def __init__(self, ..., retry_after: int | None = None):
        self.retry_after = retry_after
```

`RetryableException`を継承する例外は、呼び出し側が自動リトライを判断できる。`retry_after`で待機時間を指定可能。

#### 3. 層境界での例外変換

Infrastructure層の例外をそのまま上位層に伝播させない。層境界で適切な例外に変換する：

```python
# Infrastructure → Domain
class PoliticianRepositoryImpl:
    async def get_by_id(self, id: int) -> Politician:
        try:
            result = await self.session.get(PoliticianModel, id)
        except SQLAlchemyError as e:
            raise RepositoryError(f"DB操作失敗: {e}")  # DOM-008
```

#### 4. エラーコード体系

| プレフィックス | 層 | 用途 |
|-------------|-----|------|
| `DOM-xxx` | Domain | ビジネスルール違反、エンティティ操作エラー |
| `APP-xxx` | Application | ユースケース実行エラー、バリデーション |
| `INFRA-xxx` | Infrastructure | DB接続、外部API通信エラー |

### 採用理由

1. **Clean Architectureとの整合性**: 例外も依存性ルールに従い、内側の層は外側の層の例外を知らない
2. **運用性**: エラーコードによるログフィルタリング、アラート設定が可能
3. **自動リトライの判断**: `RetryableException`の型チェックで一時的障害と永続的エラーを区別
4. **デバッグ効率**: `details`辞書による構造化されたコンテキスト情報

## Consequences

### Positive

- ✅ エラーの出所と種類が即座に判別可能（エラーコードで）
- ✅ LLMサービスのRate Limit対応が`RetryableException`で統一的に処理可能
- ✅ Infrastructure層の技術的詳細（SQLAlchemyエラーメッセージ等）がユーザーに漏洩しない
- ✅ `details`辞書でエラーの構造化ログが自動的に記録される

### Negative

- ⚠️ 例外クラスの数が多い（現在20以上）。類似した例外が複数存在する
- ⚠️ 後方互換性のためのラッパークラス（`PolibaseError`, `ProcessingError`等）が残存
- **対策**: 段階的に後方互換ラッパーを削除予定

### Risks

- **例外の誤分類**: ドメインエラーをApplication例外として投げてしまう等
- **対策**: clean-architecture-checker SKILLで層間の依存をチェック

## References

- [ADR 0001: Clean Architecture採用](0001-clean-architecture-adoption.md)
- `src/domain/exceptions.py` - Domain層例外定義
- `src/application/exceptions.py` - Application層例外定義
- `src/infrastructure/exceptions.py` - Infrastructure層例外定義
- `.claude/skills/error-handling/` - エラーハンドリングSKILL
