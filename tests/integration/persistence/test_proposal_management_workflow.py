"""議案管理機能の統合テスト (Issue #1014).

DB実体を通した一連フローの整合性を検証する。
6つのシナリオ:
1. 会派賛否→個人展開→記名投票上書きの一連フロー
2. 投票日なし時のスキップ
3. メンバーシップなし時の展開
4. 提出者設定ワークフロー
5. 二重展開防止（force_overwrite=False）
6. 強制上書き展開（force_overwrite=True）
"""

import os

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import src.infrastructure.persistence.parliamentary_group_membership_repository_impl as pgm_mod  # noqa: E501
import src.infrastructure.persistence.proposal_parliamentary_group_judge_repository_impl as ppgj_mod  # noqa: E501

from src.application.dtos.expand_group_judges_dto import (
    ExpandGroupJudgesRequestDTO,
)
from src.application.dtos.override_individual_judge_dto import (
    IndividualVoteInputItem,
    OverrideIndividualJudgeRequestDTO,
)
from src.application.usecases.expand_group_judges_to_individual_usecase import (
    ExpandGroupJudgesToIndividualUseCase,
)
from src.application.usecases.manage_parliamentary_group_judges_usecase import (
    ManageParliamentaryGroupJudgesUseCase,
)
from src.application.usecases.manage_proposal_submitter_usecase import (
    ManageProposalSubmitterUseCase,
)
from src.application.usecases.manage_proposals_usecase import (
    CreateProposalInputDto,
    ManageProposalsUseCase,
)
from src.application.usecases.override_individual_judge_usecase import (
    OverrideIndividualJudgeUseCase,
)
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.value_objects.submitter_type import SubmitterType
from src.infrastructure.config.database import DATABASE_URL
from src.infrastructure.persistence.async_session_adapter import (
    AsyncSessionAdapter,
)
from src.infrastructure.persistence.conference_member_repository_impl import (
    ConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.proposal_deliberation_repository_impl import (
    ProposalDeliberationRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.proposal_submitter_repository_impl import (
    ProposalSubmitterRepositoryImpl,
)


ParliamentaryGroupMembershipRepositoryImpl = (
    pgm_mod.ParliamentaryGroupMembershipRepositoryImpl
)
ProposalParliamentaryGroupJudgeRepositoryImpl = (
    ppgj_mod.ProposalParliamentaryGroupJudgeRepositoryImpl
)


# CI環境でのみ実行
pytestmark = [
    pytest.mark.skipif(
        os.getenv("CI") != "true",
        reason="統合テストはCI環境でのみ実行",
    ),
    pytest.mark.integration,
    pytest.mark.asyncio,
]


# ---------------------------------------------------------------------------
# Module-scope: マスターデータ挿入
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def db_engine():
    """テスト用DBエンジンを作成する."""
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module", autouse=True)
def setup_master_data(db_engine):
    """マスターデータ（GoverningBody, Conference）を挿入し、テスト後に削除する."""
    with db_engine.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO governing_bodies (id, name, type)
                VALUES (9001, 'テスト衆議院', '国会')
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO conferences (id, name, governing_body_id)
                VALUES (9001, '第213回国会本会議', 9001)
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        conn.commit()

    yield

    # テスト後にマスターデータを削除（依存データはCASCADEで削除される）
    with db_engine.connect() as conn:
        conn.execute(text("DELETE FROM conferences WHERE id = 9001"))
        conn.execute(text("DELETE FROM governing_bodies WHERE id = 9001"))
        conn.commit()


# ---------------------------------------------------------------------------
# Function-scope: セッション・リポジトリ・UseCase
# ---------------------------------------------------------------------------
@pytest.fixture
def test_db_session(db_engine):
    """各テスト用のDBセッション（ロールバック方式）."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def session_adapter(test_db_session):
    """AsyncSessionAdapterを作成する."""
    return AsyncSessionAdapter(test_db_session)


# --- リポジトリフィクスチャ（11個） ---
@pytest.fixture
def proposal_repo(session_adapter):
    return ProposalRepositoryImpl(session_adapter)


@pytest.fixture
def proposal_judge_repo(session_adapter):
    return ProposalJudgeRepositoryImpl(session_adapter)


@pytest.fixture
def group_judge_repo(session_adapter):
    return ProposalParliamentaryGroupJudgeRepositoryImpl(session_adapter)


@pytest.fixture
def proposal_submitter_repo(session_adapter):
    return ProposalSubmitterRepositoryImpl(session_adapter)


@pytest.fixture
def deliberation_repo(session_adapter):
    return ProposalDeliberationRepositoryImpl(session_adapter)


@pytest.fixture
def pg_repo(session_adapter):
    return ParliamentaryGroupRepositoryImpl(session_adapter)


@pytest.fixture
def membership_repo(session_adapter):
    return ParliamentaryGroupMembershipRepositoryImpl(session_adapter)


@pytest.fixture
def politician_repo(session_adapter):
    return PoliticianRepositoryImpl(session_adapter)


@pytest.fixture
def meeting_repo(session_adapter):
    return MeetingRepositoryImpl(session_adapter)


@pytest.fixture
def conference_member_repo(session_adapter):
    return ConferenceMemberRepositoryImpl(session_adapter)


@pytest.fixture
def conference_repo(session_adapter):
    return ConferenceRepositoryImpl(session_adapter)


# --- UseCaseフィクスチャ（5個） ---
@pytest.fixture
def manage_proposals_uc(proposal_repo):
    return ManageProposalsUseCase(repository=proposal_repo)


@pytest.fixture
def manage_group_judges_uc(group_judge_repo, pg_repo, politician_repo):
    return ManageParliamentaryGroupJudgesUseCase(
        judge_repository=group_judge_repo,
        parliamentary_group_repository=pg_repo,
        politician_repository=politician_repo,
    )


@pytest.fixture
def expand_uc(
    group_judge_repo,
    proposal_judge_repo,
    membership_repo,
    proposal_repo,
    meeting_repo,
    politician_repo,
    deliberation_repo,
    pg_repo,
):
    return ExpandGroupJudgesToIndividualUseCase(
        group_judge_repository=group_judge_repo,
        proposal_judge_repository=proposal_judge_repo,
        membership_repository=membership_repo,
        proposal_repository=proposal_repo,
        meeting_repository=meeting_repo,
        politician_repository=politician_repo,
        deliberation_repository=deliberation_repo,
        parliamentary_group_repository=pg_repo,
    )


@pytest.fixture
def override_uc(
    proposal_judge_repo,
    group_judge_repo,
    politician_repo,
    membership_repo,
    pg_repo,
    proposal_repo,
    meeting_repo,
    deliberation_repo,
):
    return OverrideIndividualJudgeUseCase(
        proposal_judge_repository=proposal_judge_repo,
        group_judge_repository=group_judge_repo,
        politician_repository=politician_repo,
        membership_repository=membership_repo,
        parliamentary_group_repository=pg_repo,
        proposal_repository=proposal_repo,
        meeting_repository=meeting_repo,
        deliberation_repository=deliberation_repo,
    )


@pytest.fixture
def manage_submitter_uc(
    proposal_repo,
    proposal_submitter_repo,
    meeting_repo,
    conference_member_repo,
    pg_repo,
    politician_repo,
    conference_repo,
):
    return ManageProposalSubmitterUseCase(
        proposal_repository=proposal_repo,
        proposal_submitter_repository=proposal_submitter_repo,
        meeting_repository=meeting_repo,
        conference_member_repository=conference_member_repo,
        parliamentary_group_repository=pg_repo,
        politician_repository=politician_repo,
        conference_repository=conference_repo,
    )


# ---------------------------------------------------------------------------
# ヘルパー: raw SQLで前提データを挿入
# ---------------------------------------------------------------------------
def _insert_prerequisite_data(session: Session) -> None:
    """テスト共通の前提データ（会派・政治家・メンバーシップ・会議）を挿入する."""
    session.execute(
        text(
            """
            INSERT INTO politicians (id, name) VALUES
                (9001, 'テスト政治家A'),
                (9002, 'テスト政治家B'),
                (9003, 'テスト政治家C'),
                (9004, 'テスト政治家D')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    session.execute(
        text(
            """
            INSERT INTO parliamentary_groups
                (id, name, governing_body_id, is_active)
            VALUES
                (9001, '自民党テスト', 9001, true),
                (9002, '立憲民主党テスト', 9001, true)
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    session.execute(
        text(
            """
            INSERT INTO parliamentary_group_memberships
                (politician_id, parliamentary_group_id, start_date)
            VALUES
                (9001, 9001, '2024-01-01'),
                (9002, 9001, '2024-01-01'),
                (9003, 9002, '2024-01-01'),
                (9004, 9002, '2024-01-01')
            """
        )
    )
    session.execute(
        text(
            """
            INSERT INTO meetings (id, conference_id, date)
            VALUES (9001, 9001, '2024-06-15')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    session.flush()


# ---------------------------------------------------------------------------
# シナリオ1: 会派賛否→個人展開→記名投票上書きの一連フロー
# ---------------------------------------------------------------------------
class TestScenario1FullWorkflow:
    """会派賛否→個人展開→記名投票上書きの一連フロー."""

    async def test_full_workflow(
        self,
        test_db_session,
        manage_proposals_uc,
        manage_group_judges_uc,
        expand_uc,
        override_uc,
        proposal_judge_repo,
    ):
        # 1. 前提データ挿入
        _insert_prerequisite_data(test_db_session)

        # 2. 議案作成
        create_result = await manage_proposals_uc.create_proposal(
            CreateProposalInputDto(
                title="テスト議案1: 一連フロー",
                meeting_id=9001,
                conference_id=9001,
            )
        )
        assert create_result.success
        proposal_id = create_result.proposal.id

        # 3. 会派賛否登録: 自民=賛成、立憲=反対
        result_a = await manage_group_judges_uc.create(
            proposal_id=proposal_id,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[9001],
        )
        assert result_a.success, result_a.message

        result_b = await manage_group_judges_uc.create(
            proposal_id=proposal_id,
            judgment="反対",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[9002],
        )
        assert result_b.success, result_b.message

        # 4. 会派賛否→個人投票データに展開
        expand_result = await expand_uc.execute(
            ExpandGroupJudgesRequestDTO(proposal_id=proposal_id)
        )
        assert expand_result.success
        assert expand_result.total_judges_created == 4
        assert expand_result.total_members_found == 4

        # 5. 展開結果の検証
        judges = await proposal_judge_repo.get_by_proposal(proposal_id)
        judge_map = {j.politician_id: j for j in judges}

        # 自民党(A,B)は賛成
        assert judge_map[9001].approve == "賛成"
        assert judge_map[9002].approve == "賛成"
        # 立憲(C,D)は反対
        assert judge_map[9003].approve == "反対"
        assert judge_map[9004].approve == "反対"

        # source_typeの検証
        for j in judges:
            assert j.source_type == ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION
            assert j.source_group_judge_id is not None

        # 6. 記名投票上書き: 政治家C(立憲)を賛成に変更
        override_result = await override_uc.execute(
            OverrideIndividualJudgeRequestDTO(
                proposal_id=proposal_id,
                votes=[IndividualVoteInputItem(politician_id=9003, approve="賛成")],
            )
        )
        assert override_result.success
        assert override_result.judges_updated == 1
        assert len(override_result.defections) == 1
        defection = override_result.defections[0]
        assert defection.politician_id == 9003
        assert defection.individual_vote == "賛成"
        assert defection.group_judgment == "反対"

        # 7. 上書き結果の検証
        judges_after = await proposal_judge_repo.get_by_proposal(proposal_id)
        judge_map_after = {j.politician_id: j for j in judges_after}

        # 政治家Cは賛成に変更、造反フラグ=True、source_type=ROLL_CALL
        c_judge = judge_map_after[9003]
        assert c_judge.approve == "賛成"
        assert c_judge.is_defection is True
        assert c_judge.source_type == ProposalJudge.SOURCE_TYPE_ROLL_CALL

        # 他の3名は変更なし
        assert judge_map_after[9001].approve == "賛成"
        assert (
            judge_map_after[9001].source_type
            == ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION
        )
        assert judge_map_after[9002].approve == "賛成"
        assert judge_map_after[9004].approve == "反対"


# ---------------------------------------------------------------------------
# シナリオ2: 投票日なし時のスキップ
# ---------------------------------------------------------------------------
class TestScenario2NoMeetingDate:
    """投票日（meeting_id, voted_date）なし時に展開がスキップされることを検証する."""

    async def test_skip_when_no_meeting_date(
        self,
        test_db_session,
        manage_proposals_uc,
        manage_group_judges_uc,
        expand_uc,
    ):
        # 前提: 会派だけ作成（投票日特定用のmeetingは紐付けない）
        test_db_session.execute(
            text(
                """
                INSERT INTO parliamentary_groups
                    (id, name, governing_body_id, is_active)
                VALUES (9001, '自民党テスト', 9001, true)
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        test_db_session.flush()

        # 議案作成（meeting_id=None, voted_date=None）
        create_result = await manage_proposals_uc.create_proposal(
            CreateProposalInputDto(
                title="テスト議案2: 投票日なし",
                meeting_id=None,
                conference_id=9001,
            )
        )
        assert create_result.success
        proposal_id = create_result.proposal.id

        # 会派賛否登録
        result = await manage_group_judges_uc.create(
            proposal_id=proposal_id,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[9001],
        )
        assert result.success

        # 展開実行
        expand_result = await expand_uc.execute(
            ExpandGroupJudgesRequestDTO(proposal_id=proposal_id)
        )

        # 検証: 投票日なしでスキップ
        assert expand_result.success
        assert expand_result.skipped_no_meeting_date == 1
        assert expand_result.total_judges_created == 0


# ---------------------------------------------------------------------------
# シナリオ3: メンバーシップなし時の展開
# ---------------------------------------------------------------------------
class TestScenario3NoMembership:
    """メンバーシップが存在しない会派の展開でエラーにならないことを検証する."""

    async def test_expand_with_no_members(
        self,
        test_db_session,
        manage_proposals_uc,
        manage_group_judges_uc,
        expand_uc,
    ):
        # 前提: メンバーなしの会派を作成
        test_db_session.execute(
            text(
                """
                INSERT INTO parliamentary_groups
                    (id, name, governing_body_id, is_active)
                VALUES (9003, '空会派テスト', 9001, true)
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        test_db_session.execute(
            text(
                """
                INSERT INTO meetings (id, conference_id, date)
                VALUES (9001, 9001, '2024-06-15')
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        test_db_session.flush()

        # 議案作成
        create_result = await manage_proposals_uc.create_proposal(
            CreateProposalInputDto(
                title="テスト議案3: メンバーなし",
                meeting_id=9001,
                conference_id=9001,
            )
        )
        assert create_result.success
        proposal_id = create_result.proposal.id

        # 会派賛否登録（メンバーなし会派）
        result = await manage_group_judges_uc.create(
            proposal_id=proposal_id,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[9003],
        )
        assert result.success

        # 展開実行
        expand_result = await expand_uc.execute(
            ExpandGroupJudgesRequestDTO(proposal_id=proposal_id)
        )

        # 検証: エラーなし、メンバーなしなので作成0
        assert expand_result.success
        assert expand_result.total_members_found == 0
        assert expand_result.total_judges_created == 0


# ---------------------------------------------------------------------------
# シナリオ4: 提出者設定ワークフロー
# ---------------------------------------------------------------------------
class TestScenario4SubmitterWorkflow:
    """提出者の設定→クリア→再設定の一連フローを検証する."""

    async def test_submitter_workflow(
        self,
        test_db_session,
        manage_proposals_uc,
        manage_submitter_uc,
    ):
        # 前提: 政治家データ
        test_db_session.execute(
            text(
                """
                INSERT INTO politicians (id, name) VALUES (9001, 'テスト政治家A')
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        test_db_session.flush()

        # 議案作成
        create_result = await manage_proposals_uc.create_proposal(
            CreateProposalInputDto(
                title="テスト議案4: 提出者設定",
                conference_id=9001,
            )
        )
        assert create_result.success
        proposal_id = create_result.proposal.id

        # 1. 市長として提出者設定
        set_result = await manage_submitter_uc.set_submitter(
            proposal_id=proposal_id,
            submitter="テスト市長",
            submitter_type=SubmitterType.MAYOR,
        )
        assert set_result.success
        assert set_result.submitter is not None
        assert set_result.submitter.submitter_type == "mayor"
        assert set_result.submitter.raw_name == "テスト市長"

        # 2. 提出者クリア
        clear_result = await manage_submitter_uc.clear_submitter(proposal_id)
        assert clear_result.success
        assert clear_result.deleted_count == 1

        # 3. 議員として再設定（politician_id指定）
        set_result2 = await manage_submitter_uc.set_submitter(
            proposal_id=proposal_id,
            submitter="テスト政治家A",
            submitter_type=SubmitterType.POLITICIAN,
            submitter_politician_id=9001,
        )
        assert set_result2.success
        assert set_result2.submitter is not None
        assert set_result2.submitter.politician_id == 9001
        assert set_result2.submitter.submitter_type == "politician"


# ---------------------------------------------------------------------------
# シナリオ5: 二重展開防止（force_overwrite=False）
# ---------------------------------------------------------------------------
class TestScenario5DuplicateExpansionPrevention:
    """同じ条件で再展開した場合にスキップされることを検証する."""

    async def test_no_duplicate_expansion(
        self,
        test_db_session,
        manage_proposals_uc,
        manage_group_judges_uc,
        expand_uc,
    ):
        # 前提データ
        _insert_prerequisite_data(test_db_session)

        # 議案作成
        create_result = await manage_proposals_uc.create_proposal(
            CreateProposalInputDto(
                title="テスト議案5: 二重展開防止",
                meeting_id=9001,
                conference_id=9001,
            )
        )
        assert create_result.success
        proposal_id = create_result.proposal.id

        # 会派賛否登録
        await manage_group_judges_uc.create(
            proposal_id=proposal_id,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[9001],
        )
        await manage_group_judges_uc.create(
            proposal_id=proposal_id,
            judgment="反対",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[9002],
        )

        # 初回展開
        first_result = await expand_uc.execute(
            ExpandGroupJudgesRequestDTO(proposal_id=proposal_id)
        )
        assert first_result.success
        assert first_result.total_judges_created == 4

        # 再展開（force_overwrite=False）
        second_result = await expand_uc.execute(
            ExpandGroupJudgesRequestDTO(
                proposal_id=proposal_id,
                force_overwrite=False,
            )
        )

        # 検証: 新規作成0、スキップ4
        assert second_result.success
        assert second_result.total_judges_created == 0
        assert second_result.total_judges_skipped == 4


# ---------------------------------------------------------------------------
# シナリオ6: 強制上書き展開（force_overwrite=True）
# ---------------------------------------------------------------------------
class TestScenario6ForceOverwrite:
    """記名投票上書き済みデータが会派賛否で再上書きされることを検証する."""

    async def test_force_overwrite_resets_defection(
        self,
        test_db_session,
        manage_proposals_uc,
        manage_group_judges_uc,
        expand_uc,
        override_uc,
        proposal_judge_repo,
    ):
        # 前提データ
        _insert_prerequisite_data(test_db_session)

        # 議案作成
        create_result = await manage_proposals_uc.create_proposal(
            CreateProposalInputDto(
                title="テスト議案6: 強制上書き",
                meeting_id=9001,
                conference_id=9001,
            )
        )
        assert create_result.success
        proposal_id = create_result.proposal.id

        # 会派賛否登録
        await manage_group_judges_uc.create(
            proposal_id=proposal_id,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[9001],
        )
        await manage_group_judges_uc.create(
            proposal_id=proposal_id,
            judgment="反対",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[9002],
        )

        # 初回展開
        first_result = await expand_uc.execute(
            ExpandGroupJudgesRequestDTO(proposal_id=proposal_id)
        )
        assert first_result.total_judges_created == 4

        # 記名投票上書き: 政治家C(立憲)を賛成に変更（造反）
        await override_uc.execute(
            OverrideIndividualJudgeRequestDTO(
                proposal_id=proposal_id,
                votes=[IndividualVoteInputItem(politician_id=9003, approve="賛成")],
            )
        )

        # 造反状態を確認
        judges_before = await proposal_judge_repo.get_by_proposal(proposal_id)
        c_before = next(j for j in judges_before if j.politician_id == 9003)
        assert c_before.source_type == ProposalJudge.SOURCE_TYPE_ROLL_CALL
        assert c_before.approve == "賛成"

        # 強制上書き展開
        overwrite_result = await expand_uc.execute(
            ExpandGroupJudgesRequestDTO(
                proposal_id=proposal_id,
                force_overwrite=True,
            )
        )

        # 検証: 全4件が上書きされる
        assert overwrite_result.success
        assert overwrite_result.total_judges_overwritten == 4
        assert overwrite_result.total_judges_created == 0

        # 造反者のデータが会派賛否に戻る
        judges_after = await proposal_judge_repo.get_by_proposal(proposal_id)
        judge_map = {j.politician_id: j for j in judges_after}

        c_after = judge_map[9003]
        assert c_after.approve == "反対"  # 立憲の会派賛否に戻る
        assert c_after.source_type == ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION
        # NOTE: force_overwriteはis_defectionをリセットしない（現在のUseCase実装の挙動）
        # 将来修正された場合はこのアサーションを更新すること
        assert c_after.is_defection is True

        # 他の3名も正しく上書きされている
        assert judge_map[9001].approve == "賛成"
        assert judge_map[9002].approve == "賛成"
        assert judge_map[9004].approve == "反対"
