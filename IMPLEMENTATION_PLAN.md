# Issue #867 実装計画: ConferenceMember/ParliamentaryGroupMember処理への抽出ログ統合

## 1. 問題の理解

### Issue概要
会議体メンバー抽出処理と議員団メンバー抽出処理に抽出ログ機能を統合し、ConferenceMember/ParliamentaryGroupMember抽出ログを自動記録する。

### 受入条件
- [ ] 会議体メンバー抽出（baml_extractor）がUseCaseを使用している
- [ ] 議員団メンバー抽出がUseCaseを使用している
- [ ] 処理IDが各メンバー処理に紐付けられている
- [ ] エラー時もログが保存される
- [ ] パフォーマンスの劣化が5%以内
- [ ] 既存のテストが全て通る
- [ ] 統合テストが実装されている

## 2. コードベース調査の結果

### 既存のアーキテクチャ（重要）

**会議体メンバー抽出の2層構造**:
- `BAMLMemberExtractor`: 純粋なDTO抽出ロジック（`ExtractedMemberDTO`を返す）
- `ConferenceMemberExtractor.extract_and_save_members()`: エンティティ作成・保存（**統合対象**）

**議員団メンバー抽出の2層構造**:
- `BAMLParliamentaryGroupMemberExtractor`: 純粋なDTO抽出ロジック（DTOを返す）
- `ManageParliamentaryGroupsUseCase.extract_members()`: エンティティ作成・保存（**統合対象**）

### 既存のエンティティ構造

**ExtractedConferenceMember** (`src/domain/entities/extracted_conference_member.py`)
- 会議体から抽出されたメンバー情報を保存するエンティティ
- 現在、`is_manually_verified`や`latest_extraction_log_id`フィールドを**持たない**
- `VerifiableEntity`プロトコルを実装していない

**ExtractedParliamentaryGroupMember** (`src/domain/entities/extracted_parliamentary_group_member.py`)
- 議員団から抽出されたメンバー情報を保存するエンティティ
- 同様に`VerifiableEntity`プロトコルを実装していない

### 既存の抽出ログ統合パターン (PBI-004, PBI-005, PBI-006)

**UpdateEntityFromExtractionUseCase**基底クラスパターン：
- エンティティは`VerifiableEntity`プロトコルを実装
- `ExtractionResult` DTOを作成してUseCaseに渡す
- UseCaseが抽出ログを自動記録
- `is_manually_verified`フラグで人間による修正を保護

### マイグレーション状況

**最新マイグレーション**: `039_add_verification_fields_to_gold_entities.sql`
- 対象: conversations, politicians, speakers, politician_affiliations, parliamentary_group_memberships
- **`extracted_conference_members`と`extracted_parliamentary_group_members`は対象外**
- 新しいマイグレーション`040_`が必要

## 3. 技術的な解決策

### 実装アプローチ

Issue #867の要件と既存のコードベースを分析した結果、以下のアプローチを採用します：

**統合対象の場所**（Issueの記述とは異なる）:
- **会議体メンバー**: `ConferenceMemberExtractor.extract_and_save_members()` に統合
- **議員団メンバー**: `ManageParliamentaryGroupsUseCase.extract_members()` に統合

**変更しないもの**:
- `BAMLMemberExtractor`: そのまま（純粋なDTO抽出ロジック）
- `BAMLParliamentaryGroupMemberExtractor`: そのまま（純粋なDTO抽出ロジック）
- `IMemberExtractorService`: インターフェース変更不要
- `IParliamentaryGroupMemberExtractorService`: インターフェース変更不要
- `MemberExtractorFactory`: Factory変更不要

理由：
1. 2層構造を維持（抽出ロジックとエンティティ保存の分離）
2. 既存のPBI-004, PBI-005, PBI-006と同じパターンを踏襲
3. 既存のインターフェースを変更しないため、既存コードへの影響が最小限
4. データの一貫性とトレーサビリティの確保

### 実装の詳細

#### 1. エンティティの更新

**ExtractedConferenceMemberエンティティ**
- `is_manually_verified: bool = False`フィールドを追加
- `latest_extraction_log_id: int | None = None`フィールドを追加
- `mark_as_manually_verified()`メソッドを追加
- `update_from_extraction_log(log_id: int)`メソッドを追加
- `can_be_updated_by_ai()`メソッドを追加

**ExtractedParliamentaryGroupMemberエンティティ**
- 同様のフィールドとメソッドを追加

**データベースマイグレーション** (`040_add_extraction_log_fields_to_extracted_members.sql`)
- `extracted_conference_members`テーブルに以下のカラムを追加:
  - `is_manually_verified BOOLEAN NOT NULL DEFAULT FALSE`
  - `latest_extraction_log_id INTEGER REFERENCES extraction_logs(id)`
- `extracted_parliamentary_group_members`テーブルに同様のカラムを追加

#### 2. ExtractionResult DTOの作成

**ConferenceMemberExtractionResult** (`src/application/dtos/extraction_result/conference_member_extraction_result.py`)
```python
@dataclass
class ConferenceMemberExtractionResult:
    """会議体メンバーのAI抽出結果を表すDTO."""
    conference_id: int
    extracted_name: str
    source_url: str
    extracted_role: str | None = None
    extracted_party_name: str | None = None
    additional_data: str | None = None
    confidence_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

**ParliamentaryGroupMemberExtractionResult** (`src/application/dtos/extraction_result/parliamentary_group_member_extraction_result.py`)
```python
@dataclass
class ParliamentaryGroupMemberExtractionResult:
    """議員団メンバーのAI抽出結果を表すDTO."""
    parliamentary_group_id: int
    extracted_name: str
    source_url: str
    extracted_role: str | None = None
    extracted_party_name: str | None = None
    extracted_district: str | None = None
    additional_info: str | None = None
    confidence_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

#### 3. UseCaseの作成

**UpdateExtractedConferenceMemberFromExtractionUseCase**
- `UpdateEntityFromExtractionUseCase`を継承
- `_get_entity_type()`: `EntityType.CONFERENCE_MEMBER`を返す
- `_get_entity()`: `ExtractedConferenceMemberRepository.get_by_id()`を呼び出す
- `_save_entity()`: `ExtractedConferenceMemberRepository.update()`を呼び出す
- `_to_extracted_data()`: `result.to_dict()`を呼び出す
- `_apply_extraction()`: 抽出結果をエンティティに適用

**UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase**
- 同様のパターンで実装

#### 4. 抽出処理へのUseCase統合

**会議体メンバー: ConferenceMemberExtractor.extract_and_save_members()への統合**

```python
# src/infrastructure/external/conference_member_extractor/extractor.py

class ConferenceMemberExtractor:
    def __init__(
        self,
        update_usecase: UpdateExtractedConferenceMemberFromExtractionUseCase | None = None,
    ):
        self._extractor = MemberExtractorFactory.create()  # 変更なし
        self.repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)
        self._update_usecase = update_usecase

    async def extract_and_save_members(
        self, conference_id: int, conference_name: str, url: str
    ) -> dict[str, Any]:
        # ... 既存の処理 ...

        for member in members:
            # エンティティを作成
            entity = ExtractedConferenceMember(...)
            created_entity = await self.repo.create(entity)

            # 抽出ログを記録（UseCaseがあれば）
            if self._update_usecase and created_entity.id:
                try:
                    extraction_result = ConferenceMemberExtractionResult(...)
                    await self._update_usecase.execute(
                        entity_id=created_entity.id,
                        extraction_result=extraction_result,
                        pipeline_version="conference-member-extractor-v1",
                    )
                except Exception as e:
                    logger.warning(f"Failed to log extraction: {e}")
                    # エラー時も処理は継続
```

**議員団メンバー: ManageParliamentaryGroupsUseCase.extract_members()への統合**

```python
# src/application/usecases/manage_parliamentary_groups_usecase.py

class ManageParliamentaryGroupsUseCase:
    def __init__(
        self,
        ...,
        update_extracted_member_usecase: UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase | None = None,
    ):
        ...
        self._update_extracted_member_usecase = update_extracted_member_usecase

    async def extract_members(self, input_dto: ExtractMembersInputDto) -> ExtractMembersOutputDto:
        # ... 既存の処理 ...

        for entity in entities_to_save:
            # bulk_createの後、各エンティティに対して抽出ログを記録
            if self._update_extracted_member_usecase and entity.id:
                try:
                    extraction_result = ParliamentaryGroupMemberExtractionResult(...)
                    await self._update_extracted_member_usecase.execute(
                        entity_id=entity.id,
                        extraction_result=extraction_result,
                        pipeline_version="parliamentary-group-member-extractor-v1",
                    )
                except Exception as e:
                    logger.warning(f"Failed to log extraction: {e}")
```

## 4. 実装計画

### Phase 1: エンティティとマイグレーション

#### タスク1.1: ExtractedConferenceMemberエンティティの更新
- ファイル: `src/domain/entities/extracted_conference_member.py`
- 追加フィールド: `is_manually_verified`, `latest_extraction_log_id`
- 追加メソッド: `mark_as_manually_verified()`, `update_from_extraction_log()`, `can_be_updated_by_ai()`

#### タスク1.2: ExtractedParliamentaryGroupMemberエンティティの更新
- ファイル: `src/domain/entities/extracted_parliamentary_group_member.py`
- 同様のフィールドとメソッドを追加

#### タスク1.3: データベースマイグレーション
- ファイル: `database/migrations/040_add_extraction_log_fields_to_extracted_members.sql`
- `extracted_conference_members`と`extracted_parliamentary_group_members`テーブルにカラムを追加
- `database/02_run_migrations.sql`に追加

### Phase 2: DTO作成

#### タスク2.1: ConferenceMemberExtractionResult作成
- ファイル: `src/application/dtos/extraction_result/conference_member_extraction_result.py`

#### タスク2.2: ParliamentaryGroupMemberExtractionResult作成
- ファイル: `src/application/dtos/extraction_result/parliamentary_group_member_extraction_result.py`

#### タスク2.3: __init__.pyの更新
- ファイル: `src/application/dtos/extraction_result/__init__.py`

### Phase 3: UseCase作成

#### タスク3.1: UpdateExtractedConferenceMemberFromExtractionUseCase作成
- ファイル: `src/application/usecases/update_extracted_conference_member_from_extraction_usecase.py`

#### タスク3.2: UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase作成
- ファイル: `src/application/usecases/update_extracted_parliamentary_group_member_from_extraction_usecase.py`

#### タスク3.3: __init__.pyの更新
- ファイル: `src/application/usecases/__init__.py`

### Phase 4: 抽出処理への統合

#### タスク4.1: ConferenceMemberExtractorの更新
- ファイル: `src/infrastructure/external/conference_member_extractor/extractor.py`
- `UpdateExtractedConferenceMemberFromExtractionUseCase`を依存性注入（オプショナル）
- `extract_and_save_members()`内でエンティティ保存後に抽出ログを記録
- **注意**: `BAMLMemberExtractor`は変更なし

#### タスク4.2: ManageParliamentaryGroupsUseCaseの更新
- ファイル: `src/application/usecases/manage_parliamentary_groups_usecase.py`
- `UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase`を依存性注入（オプショナル）
- `extract_members()`内でエンティティ保存後に抽出ログを記録
- **注意**: `BAMLParliamentaryGroupMemberExtractor`は変更なし

### Phase 5: DIコンテナの更新

#### タスク5.1: DIコンテナの更新
- ファイル: `src/infrastructure/di/providers.py`
- UseCaseをコンテナに登録
- `ConferenceMemberExtractor`と`ManageParliamentaryGroupsUseCase`に依存性を注入

#### タスク5.2: 使用箇所の更新
- `src/interfaces/web/streamlit/views/conferences_view.py`: `ConferenceMemberExtractor()`をDI経由に変更
- `src/interfaces/cli/commands/conference_member_commands.py`: 同様
- `src/interfaces/web/streamlit/presenters/parliamentary_group_presenter.py`: UseCaseにDI注入

### Phase 6: テストの作成

#### タスク6.1: 統合テストの作成
- ファイル: `tests/integration/test_conference_member_extractor_with_extraction_log.py`
- 会議体メンバー抽出時の抽出ログ記録テスト
- エラー時のログ記録テスト

#### タスク6.2: 統合テストの作成
- ファイル: `tests/integration/test_parliamentary_group_member_extractor_with_extraction_log.py`
- 議員団メンバー抽出時の抽出ログ記録テスト

#### タスク6.3: 既存テストの更新
- `ConferenceMemberExtractor`のテストを更新（モックの追加）
- `ManageParliamentaryGroupsUseCase`のテストを更新（モックの追加）
- **注意**: `BAMLMemberExtractor`と`BAMLParliamentaryGroupMemberExtractor`のテストは変更不要

## 5. リスクと注意点

### リスク1: データベーススキーマの変更
- 既存データへの影響を最小化するため、デフォルト値を設定
- ロールバック手順を準備

### リスク2: 2段階処理のパフォーマンス
- エンティティ作成と抽出ログ記録の2回のDB書き込み
- トランザクション管理の複雑化

### リスク3: 既存コードへの影響
- `ConferenceMemberExtractor`と`ManageParliamentaryGroupsUseCase`のコンストラクタ変更
- 既存の使用箇所（CLI、Streamlit UI）でのインスタンス化方法を更新する必要がある
- **注意**: `BAMLMemberExtractor`と`BAMLParliamentaryGroupMemberExtractor`は変更不要のため、低リスク

## 6. 実装の順序

1. Phase 1: エンティティとマイグレーション
2. Phase 2: DTO作成
3. Phase 3: UseCase作成
4. Phase 4: 抽出処理への統合
5. Phase 5: DIコンテナの更新
6. Phase 6: テストの作成と既存テストの更新
7. 動作確認とパフォーマンステスト

## 7. 期待される成果

- ✅ 会議体メンバー抽出処理が抽出ログを自動記録
- ✅ 議員団メンバー抽出処理が抽出ログを自動記録
- ✅ 処理IDが各メンバー処理に紐付けられている
- ✅ エラー時もログが保存される
- ✅ パフォーマンスの劣化が5%以内
- ✅ 既存のテストが全て通る
- ✅ 統合テストが実装されている
