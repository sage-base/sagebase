# ADR 0010: Application層でのトランザクション管理戦略

## Status

Accepted (2026-03-13)

## Context

### 背景

Clean Architecture（ADR 0001）とリポジトリパターン（ADR 0003）を採用した結果、トランザクション管理の責務をどの層に配置するかが設計上の重要な判断事項となりました。

トランザクション境界の設定場所は、Clean Architectureにおいて明確な正解がありません。以下の3つの選択肢がありました：

### 検討した代替案

#### 1. Infrastructure層（リポジトリ内）でのトランザクション管理

```python
# ❌ リポジトリ内でcommit
class PoliticianRepositoryImpl:
    async def create(self, entity: Politician) -> Politician:
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.commit()  # ❌ リポジトリがcommitする
        return self._to_entity(model)
```

**問題点**:
- 複数リポジトリにまたがる操作で部分的コミットが発生する
- 政治家作成 + 会派メンバーシップ登録のようなアトミック操作が保証できない
- リポジトリの再利用性が低下する（単独でしか使えない）

#### 2. Interface層（CLIコマンド/Streamlit）でのトランザクション管理

```python
# △ Interface層でcommit
async def process_minutes_command(meeting_id: int):
    async with get_db_session() as session:
        use_case = ProcessMinutesUseCase(...)
        result = await use_case.execute(request)
        if result.success:
            await session.commit()
```

**問題点**:
- トランザクション境界がUIの実装に依存する
- 同じユースケースを異なるInterface（CLI, Web）から呼ぶとき、一貫性が保てない

#### 3. Application層（ユースケース）でのトランザクション管理（選択）

```python
# ✅ ユースケースがトランザクション境界を定義
class ProcessMinutesUseCase:
    async def execute(self, request: ProcessMinutesDTO):
        politician = await self.politician_repo.create(politician)
        await self.membership_repo.create(membership)
        # ユースケースの成功をもってコミット
```

## Decision

**トランザクション管理はApplication層（ユースケース）の責務とする。**

### 実装方針

#### 1. リポジトリは`flush()`のみ、`commit()`はしない

リポジトリ層のメソッドは`flush()`で変更をデータベースに送信するが、`commit()`は呼ばない。これにより、呼び出し側（ユースケース）がトランザクションの最終的な確定を制御できる。

```python
# BaseRepositoryImpl
async def create(self, entity: T) -> T:
    model = self._to_model(entity)
    self.session.add(model)
    await self.session.flush()    # DBに送信するがcommitしない
    await self.session.refresh(model)
    return self._to_entity(model)
```

#### 2. ユースケース単位 = 1トランザクション

1つのユースケースメソッドの実行が1つのトランザクションに対応する。複数のリポジトリ操作がアトミックに実行される。

#### 3. セッションのライフサイクル管理はDIコンテナ/Interface層が担当

セッションの生成と注入はDIコンテナが行い、commitのタイミングはInterface層がユースケースの結果を見て判断する。ユースケースはセッション管理の詳細を知らない。

```python
# Interface層でのセッション管理パターン
async with get_db_session() as session:
    repo = PoliticianRepositoryImpl(session)
    use_case = ManagePoliticiansUseCase(repo)
    result = await use_case.execute(input_dto)
    if result.success:
        await session.commit()
    else:
        await session.rollback()
```

### 採用理由

1. **ビジネストランザクションとの一致**: 1ユースケース = 1ビジネストランザクションが自然な単位
2. **アトミック操作の保証**: 複数リポジトリにまたがる操作が確実にアトミックになる
3. **Interface非依存**: CLI/Streamlitのどちらから呼んでも同じトランザクション境界
4. **テスト容易性**: ユースケース単位でトランザクションの成否をテスト可能

## Consequences

### Positive

- ✅ 複数リポジトリ操作のアトミック性が保証される
- ✅ トランザクション境界がビジネスロジックの単位と一致する
- ✅ リポジトリの再利用性が向上する（単独でもcompositionでも使える）
- ✅ Interface層の実装バリエーション（CLI, Web, API）に対して一貫性を保てる

### Negative

- ⚠️ セッションのスコープ管理がInterface層に残るため、完全なApplication層の独立性ではない
- ⚠️ 長時間実行ユースケースでのデータベースロック保持のリスク
- **対策**: 長時間処理はバッチ分割し、ユースケース内で段階的にcommitする

### Risks

- **セッションリーク**: Interface層でのセッション管理漏れ → `async with`パターンで防止
- **flush忘れ**: リポジトリで`flush()`を呼ばないとID生成されない → BaseRepositoryImplで統一

## References

- [ADR 0001: Clean Architecture採用](0001-clean-architecture-adoption.md)
- [ADR 0003: リポジトリパターン + ISessionAdapter](0003-repository-pattern.md)
- `src/infrastructure/persistence/base_repository_impl.py` - flush()パターンの実装
- `src/infrastructure/di/providers.py` - セッションライフサイクル管理
