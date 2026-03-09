# Polibase 非政治家・官僚システム アーキテクチャ調査報告

## 1. エンティティ定義 (Domain Layer)

### GovernmentOfficial (政府関係者)
**ファイル**: `src/domain/entities/government_official.py`
- `id: int` - プライマリキー
- `name: str` - 名前（必須）
- `name_yomi: str | None` - 読み仮名

**実装**: シンプルなエンティティ。政府参考人・官僚・説明員等を表す。

### GovernmentOfficialPosition (政府関係者の役職履歴)
**ファイル**: `src/domain/entities/government_official_position.py`
- `government_official_id: int` - FK to government_officials
- `organization: str` - 所属団体（e.g., "内閣官房"）
- `position: str` - 役職（e.g., "参考人"）
- `start_date: date | None` - 役職開始日
- `end_date: date | None` - 役職終了日
- `source_note: str | None` - 出典など

**メソッド**: `is_active(as_of_date)` - 指定日時点での有効性判定

## 2. Speaker エンティティの拡張
**ファイル**: `src/domain/entities/speaker.py`

Speaker に非政治家関連のフィールドを追加:
- `government_official_id: int | None` - GovernmentOfficialへの紐付けID
- `skip_reason: str | None` - 非政治家分類理由（SkipReason enum値）
- `is_politician: bool` - 政治家フラグ（デフォルト False）

**重要メソッド**:
```python
def link_to_government_official(self, government_official_id: int) -> None:
    """政府関係者に紐付ける.
    government_official_id を設定し、is_politician=False、
    skip_reason="government_official" に設定する。
    """
```

## 3. データベーススキーマ（Alembic Migration）

**ファイル**: `alembic/versions/039_add_government_officials.py`

### 新規テーブル

#### government_officials
```sql
CREATE TABLE government_officials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    name_yomi VARCHAR(200),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_government_officials_name ON government_officials(name);
```

#### government_official_positions
```sql
CREATE TABLE government_official_positions (
    id SERIAL PRIMARY KEY,
    government_official_id INTEGER NOT NULL
        REFERENCES government_officials(id) ON DELETE CASCADE,
    organization VARCHAR(200) NOT NULL,
    position VARCHAR(200) NOT NULL,
    start_date DATE,
    end_date DATE,
    source_note VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_gop_end_date_after_start
        CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE INDEX idx_gop_official_id ON government_official_positions(government_official_id);
CREATE INDEX idx_gop_organization ON government_official_positions(organization);
```

### 既存テーブル修正

#### speakers
```sql
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS government_official_id INTEGER
    REFERENCES government_officials(id) ON DELETE SET NULL;
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS skip_reason VARCHAR;
CREATE INDEX idx_speakers_gov_official_id ON speakers(government_official_id)
    WHERE government_official_id IS NOT NULL;
```

## 4. リポジトリインターフェース（Domain Layer）

### GovernmentOfficialRepository
**ファイル**: `src/domain/repositories/government_official_repository.py`

```python
class GovernmentOfficialRepository(BaseRepository[GovernmentOfficial]):
    @abstractmethod
    async def get_by_name(self, name: str) -> GovernmentOfficial | None:
        """名前で政府関係者を取得する."""

    @abstractmethod
    async def search_by_name(self, name: str) -> list[GovernmentOfficial]:
        """名前の部分一致で政府関係者を検索する."""
```

### GovernmentOfficialPositionRepository
**ファイル**: `src/domain/repositories/government_official_position_repository.py`

```python
class GovernmentOfficialPositionRepository(BaseRepository[GovernmentOfficialPosition]):
    @abstractmethod
    async def get_by_official(self, government_official_id: int)
        -> list[GovernmentOfficialPosition]:
        """政府関係者IDで役職履歴を取得する."""

    @abstractmethod
    async def get_active_by_official(self, government_official_id: int,
        as_of_date: date | None = None) -> list[GovernmentOfficialPosition]:
        """政府関係者IDで有効な役職を取得する."""

    @abstractmethod
    async def bulk_upsert(self, positions: list[GovernmentOfficialPosition])
        -> list[GovernmentOfficialPosition]:
        """役職履歴を一括upsertする（official_id + organization + position + start_dateで一意性判定）."""
```

## 5. リポジトリ実装（Infrastructure Layer）

### GovernmentOfficialRepositoryImpl
**ファイル**: `src/infrastructure/persistence/government_official_repository_impl.py`

- SQLAlchemy ORM実装
- BaseRepositoryImpl を継承（完全互換）
- `_to_entity()`, `_to_model()`, `_update_model()` で型変換

### GovernmentOfficialPositionRepositoryImpl
**ファイル**: `src/infrastructure/persistence/government_official_position_repository_impl.py`

- SQLAlchemy ORM実装
- `bulk_upsert()` で既存チェック→update/create の処理を実装

## 6. ドメインサービス（Domain Layer）

### SpeakerClassifier (話者分類)
**ファイル**: `src/domain/services/speaker_classifier.py`

**SkipReason Enum**:
```python
class SkipReason(Enum):
    ROLE_ONLY = "role_only"              # 役職のみ（「議長」「委員長」等）
    REFERENCE_PERSON = "reference_person"    # 参考人・証人・公述人
    GOVERNMENT_OFFICIAL = "government_official"  # 政府側（「政府参考人」「政府委員」等）
    OTHER_NON_POLITICIAN = "other_non_politician"   # その他（事務局長、書記官長等）
    HOMONYM = "homonym"                 # 同姓同名
```

**分類パターン**:
- **完全一致**: `NON_POLITICIAN_EXACT_NAMES` frozenset
  - 政府側: {"説明員", "政府委員", "政府参考人"}
  - 参考人: {"参考人", "証人", "公述人"}
  - その他: {"事務局長", "事務局次長", "事務総長", "法制局長", "書記官長", "速記者", "幹事", "会議録情報"}

- **プレフィックスマッチ**: `NON_POLITICIAN_PREFIX_PATTERNS` frozenset
  - 「政府参考人（山田太郎君）」形式に対応
  - プレフィックス: {"政府参考人（", "政府委員（", "説明員（", "参考人（", "証人（", ...}

**関数**:
```python
def is_non_politician_name(name: str) -> bool:
    """指定された名前が非政治家パターンに該当するかを判定する."""

def classify_speaker_skip_reason(name: str) -> SkipReason | None:
    """発言者名を分類し、非政治家カテゴリを返す."""
```

## 7. Application Layer (Use Cases)

### LinkSpeakerToGovernmentOfficialUseCase
**ファイル**: `src/application/usecases/link_speaker_to_government_official_usecase.py`

- Speaker と GovernmentOfficial を紐付け
- **優先度ルール**: politician_id が既に設定されている場合は紐付け不可
- `speaker.link_to_government_official(government_official_id)` で設定

**入出力DTO**:
```python
@dataclass
class LinkSpeakerToGovernmentOfficialInputDto:
    speaker_id: int
    government_official_id: int

@dataclass
class LinkSpeakerToGovernmentOfficialOutputDto:
    success: bool
    error_message: str | None = None
```

### MarkSpeakerAsNonPoliticianUseCase
**ファイル**: `src/application/usecases/mark_speaker_as_non_politician_usecase.py`

- 個別の Speaker に対してSkipReasonを設定
- `is_politician=False`, `politician_id=None`, `skip_reason=<理由>` を設定

**入出力DTO**:
```python
@dataclass
class MarkSpeakerAsNonPoliticianInputDto:
    speaker_id: int
    skip_reason: str

@dataclass
class MarkSpeakerAsNonPoliticianOutputDto:
    success: bool
    error_message: str | None = None
```

### ClassifySpeakersPoliticianUseCase
**ファイル**: `src/application/usecases/classify_speakers_politician_usecase.py`

- **全 Speaker に対する一括分類**
- `speaker_repository.classify_is_politician_bulk()` を呼び出し
- SQLで一括実行: is_politician フラグをリセット → パターンマッチングで非政治家に設定

### ImportGovernmentOfficialsCsvUseCase
**ファイル**: `src/application/usecases/import_government_officials_csv_usecase.py`

- CSV行から GovernmentOfficial を find-or-create
- GovernmentOfficialPosition を bulk_upsert
- **同名Speaker全件を自動紐付け** (politician_id が NULL の場合のみ)

**処理フロー**:
1. CSV行を読み込み
2. speaker_name で GovernmentOfficial.get_by_name()
3. 存在しなければ新規作成
4. GovernmentOfficialPosition を upsert
5. 同名 Speaker を search_by_name() で探す
6. politician_id が NULL なら link_to_government_official()

## 8. Speaker Repository の Bulk処理

### classify_is_politician_bulk()
**ファイル**: `src/infrastructure/persistence/speaker_repository_impl.py` (L760-839)

```python
async def classify_is_politician_bulk(
    self,
    non_politician_names: frozenset[str],
    non_politician_prefixes: frozenset[str] | None = None,
    skip_reason_patterns: list[tuple[str, frozenset[str], frozenset[str]]] | None = None
) -> dict[str, int]:
    """全Speakerのis_politicianフラグを一括分類設定する.

    処理:
    1. 全件を is_politician=TRUE にリセット（skip_reason=NULL）
    2. 非政治家パターンマッチングで is_politician=FALSE に戻す
    3. skip_reason_patterns が指定された場合、カテゴリ別にskip_reasonも設定
    """
```

**処理の優先度**:
- `politician_id IS NOT NULL` → スキップ（既にマッチ済みのため変更しない）
- `is_manually_verified = TRUE` → スキップ（手動検証済み）

## 9. DTO定義

**ファイル**: `src/application/dtos/government_official_dto.py`

```python
@dataclass
class GovernmentOfficialOutputItem:
    id: int
    name: str
    name_yomi: str | None = None
    positions: list[GovernmentOfficialPositionOutputItem] = field(default_factory=list)

@dataclass
class GovernmentOfficialPositionOutputItem:
    id: int
    government_official_id: int
    organization: str
    position: str
    start_date: date | None = None
    end_date: date | None = None
    source_note: str | None = None

@dataclass
class LinkSpeakerToGovernmentOfficialInputDto:
    speaker_id: int
    government_official_id: int

@dataclass
class ImportGovernmentOfficialsCsvInputDto:
    rows: list[GovernmentOfficialCsvRow]
    dry_run: bool = False

@dataclass
class ImportGovernmentOfficialsCsvOutputDto:
    created_officials_count: int = 0
    created_positions_count: int = 0
    linked_speakers_count: int = 0
    skipped_count: int = 0
    errors: list[str] = field(default_factory=list)
```

## 10. Speaker と非政治家紐付けの優先度ルール

**紐付け対象の優先順位**:
1. `politician_id` (政治家マッチング) - **最優先**
2. `government_official_id` (官僚マッチング)
3. `skip_reason` (非政治家分類)

**制約**:
- `politician_id` が既に設定されている Speaker には `government_official_id` を設定不可
- `government_official_id` が既に設定されている Speaker には `politician_id` を設定不可（暗黙的）

## 11. UI での使用箇所

**Streamlit タブ**: `src/interfaces/web/streamlit/views/conversations/tabs/speakers_list_tab.py`

- 発言者一覧表示
- SkipReason でフィルタ可能
- 手動で Speaker → GovernmentOfficial または Politician に紐付け可能
- 非政治家分類を個別に実行可能

## 12. SQL Models

**ファイル**: `src/infrastructure/persistence/sqlalchemy_models.py`

```python
# SpeakerModel
class SpeakerModel(Base):
    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_politician: Mapped[bool] = mapped_column(Boolean, default=False)
    politician_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("politicians.id", use_alter=True, name="fk_speaker_politician"),
    )
    government_official_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("government_officials.id", use_alter=True, name="fk_speaker_gov_official"),
    )
    skip_reason: Mapped[str | None] = mapped_column(String)
    is_manually_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # ... other fields ...

class GovernmentOfficialModel(Base):
    __tablename__ = "government_officials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_yomi: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class GovernmentOfficialPositionModel(Base):
    __tablename__ = "government_official_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    government_official_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("government_officials.id", ondelete="CASCADE"),
    )
    organization: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date | None] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    source_note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

## 重要な設計ポイント

1. **二重紐付け防止**: Speaker が同時に politician_id と government_official_id を持つことはない
2. **SkipReasonの目的**: 非政治家である理由を分類し、UI でのフィルタリングや統計に活用
3. **手動検証フラグ**: `is_manually_verified=True` の Speaker は AI による自動更新対象外
4. **一括分類処理**: 全 Speaker に対してパターンマッチングで一括設定し、効率的に非政治家を振り分け
5. **CSV インポート**: GovernmentOfficial の一括追加と同時に Speaker への自動紐付けを実行
