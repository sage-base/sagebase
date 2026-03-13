# ADR 0011: LLMサービスのデコレーターパターン

## Status

Accepted (2026-03-13)

## Context

### 背景

SagebaseではLLM（Gemini API）を議事録分割、政治家マッチング、議員団メンバー抽出などの中核機能で使用しています。LLM呼び出しには以下の横断的関心事（cross-cutting concerns）が伴います：

- **コスト管理**: トークン使用量の計測と履歴記録
- **パフォーマンス**: レスポンス時間の計測、レート制限への対応
- **信頼性**: リトライ、キャッシュ、並行制御
- **トレーサビリティ**: 処理履歴の記録、デバッグ情報の保持

これらの関心事を単一のLLMサービスクラスに実装すると、クラスが肥大化し、関心事の分離ができなくなります。

### 課題: 単一クラスでの実装

```python
# ❌ すべての関心事が1クラスに混在
class GeminiLLMService:
    async def extract_speeches(self, text):
        # キャッシュチェック
        # メトリクス計測開始
        # レート制限チェック
        # 実際のLLM呼び出し
        # 履歴記録
        # メトリクス記録
        # キャッシュ保存
        pass  # 数百行のメソッド
```

### 検討した代替案

#### 1. ミドルウェアチェーン（LangChain Callbacks）

LangChainの`Callbacks`機構を使ってフック処理を差し込む方式。

**欠点**: LangChainのコールバックAPIに強く依存する。SagebaseではBAML（ADR 0002）を併用しているため、LangChain固有の機構に依存するのは不適切。

#### 2. AOP（Aspect-Oriented Programming）

デコレーターやメタクラスで横断的関心事を自動的に適用する方式。

**欠点**: Pythonでは暗黙的な振る舞いが増えてデバッグが困難。明示的な構成が望ましい。

#### 3. デコレーターパターン（選択）

`ILLMService`インターフェースを実装するラッパークラスを層状に組み合わせる方式。

## Decision

**LLMサービスにデコレーターパターンを採用し、3つの独立したラッパーで横断的関心事を分離する。**

### 3つのデコレーター

#### 1. `InstrumentedLLMService` — 計測・履歴記録

```
GeminiLLMService → InstrumentedLLMService
```

- **責務**: LLM呼び出しの履歴記録（`llm_processing_history`テーブル）、レスポンス時間計測、トークン使用量追跡、OpenTelemetryメトリクス
- **エラーコード体系**: 処理ステータス（成功/失敗/リトライ）の記録
- **リトライ**: `invoke_with_retry()`による自動リトライ（Rate Limit対応）

#### 2. `CachedLLMService` — キャッシュ・バッチ処理

```
(Inner Service) → CachedLLMService
```

- **責務**: 同一入力に対するLLM呼び出しのキャッシュ、バッチリクエストの集約
- **キャッシュキー**: 入力テキストのハッシュベース
- **用途**: 議事録の再処理時など、同一データへの重複呼び出し防止

#### 3. `ConcurrentLLMService` — 並行制御・レート制限

```
(Inner Service) → ConcurrentLLMService
```

- **責務**: 同時実行数の制限（`asyncio.Semaphore`）、レート制限への対応、バッチ処理の並行実行
- **設定**: `max_concurrent`（最大同時実行数）、`rate_limiter`（レート制限器）

### 組み合わせパターン

DIコンテナ（`providers.py`）で必要なデコレーターを組み合わせる：

```python
# 基本サービス
base = GeminiLLMService(api_key=key, model_name="gemini-2.0-flash")

# 計測付き
instrumented = InstrumentedLLMService(base, history_repo, prompt_repo)

# 計測 + 並行制御
concurrent = ConcurrentLLMService(instrumented, max_concurrent=5)

# 計測 + キャッシュ
cached = CachedLLMService(instrumented)
```

### 採用理由

1. **関心事の分離**: 各デコレーターが1つの関心事のみ担当
2. **柔軟な組み合わせ**: ユースケースに応じて必要なデコレーターのみ適用
3. **テスト容易性**: 各デコレーターを個別にテスト可能
4. **開放/閉鎖原則**: 新しい関心事は新しいデコレーターとして追加（既存コード変更不要）
5. **BAML互換**: LangChain固有の機構に依存しない汎用的な設計

## Consequences

### Positive

- ✅ LLMサービスの各関心事が明確に分離される
- ✅ テスト時に不要なデコレーターを除外して高速テスト可能
- ✅ 新しい関心事（例: コスト制限、A/Bテスト）を既存コード変更なしで追加可能
- ✅ `__getattr__`による透過的なメソッド委譲で、基底サービスの全メソッドが自動的に利用可能

### Negative

- ⚠️ デバッグ時にコールスタックが深くなる（3〜4層のラッピング）
- ⚠️ デコレーターの適用順序が重要（例: Instrumentedが最内側だと計測にキャッシュヒットが含まれない）
- **対策**: DIコンテナでの組み立て順序を統一し、ドキュメント化

### Risks

- **インターフェース変更時の影響**: `ILLMService`のメソッド追加時、全デコレーターの更新が必要
- **対策**: `__getattr__`で基底サービスへの委譲をデフォルトにし、明示的にオーバーライドするメソッドのみ各デコレーターに実装

## References

- [ADR 0002: BAML for LLM Outputs](0002-baml-for-llm-outputs.md)
- `src/infrastructure/external/instrumented_llm_service.py` - 計測デコレーター
- `src/infrastructure/external/cached_llm_service.py` - キャッシュデコレーター
- `src/infrastructure/external/concurrent_llm_service.py` - 並行制御デコレーター
- `src/infrastructure/external/llm_service.py` - 基底LLMサービス（GeminiLLMService）
- `src/infrastructure/di/providers.py` - デコレーター組み立て
