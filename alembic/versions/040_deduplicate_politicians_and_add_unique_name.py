"""politiciansテーブルの重複レコード削除とname UNIQUE制約追加.

Revision ID: 040
Revises: 039
Create Date: 2026-03-09

補欠選挙SEEDデータ投入時（PR #1327）に重複politicianの存在が発覚。
同名の重複レコードを統合し、再発防止のためname列にUNIQUE制約を追加する。

対象:
- 岡元義人 (id: 17162残す, 17171削除)
- 浜田聡 (id: 13233残す, 13234削除)
- 宮本しゅうじ (id: 9544残す, 17199削除)
- アントニオ猪木 (id: 6329残す, 6330削除)
- 齊藤健一郎 (id: 16844残す, 16845削除)

Refs: #1328
"""

from alembic import op


revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """重複politicianを統合し、name UNIQUE制約を追加."""
    # Step 1: 同名の重複politicianを動的に検出し、FK参照を残すIDに付け替えてから削除
    # 残すID = furiganaがある方、またはIDが小さい方を優先
    op.execute("""
        -- 重複politicianの統合: 残すIDにFK参照を付け替え、重複を削除
        -- keep_id: furiganaがNULLでない方を優先、同じならIDが小さい方
        -- delete_id: 削除対象
        DO $$
        DECLARE
            dup RECORD;
        BEGIN
            FOR dup IN
                SELECT
                    keep.id AS keep_id,
                    del.id AS delete_id
                FROM (
                    SELECT name
                    FROM politicians
                    GROUP BY name
                    HAVING COUNT(*) > 1
                ) dupes
                CROSS JOIN LATERAL (
                    SELECT id
                    FROM politicians p
                    WHERE p.name = dupes.name
                    ORDER BY
                        CASE WHEN p.furigana IS NOT NULL THEN 0 ELSE 1 END,
                        p.id
                    LIMIT 1
                ) keep
                CROSS JOIN LATERAL (
                    SELECT id
                    FROM politicians p
                    WHERE p.name = dupes.name AND p.id != keep.id
                    ORDER BY p.id
                ) del
            LOOP
                -- FK参照を残すIDに付け替え
                -- UNIQUE制約がないテーブルは単純UPDATE
                UPDATE speakers SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;
                UPDATE pledges SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;
                UPDATE party_membership_history SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;
                UPDATE parliamentary_group_memberships SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;
                UPDATE proposal_judges SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;
                UPDATE conference_members SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;
                UPDATE proposal_submitters SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;
                UPDATE extracted_conference_members SET matched_politician_id = dup.keep_id
                    WHERE matched_politician_id = dup.delete_id;
                UPDATE extracted_parliamentary_group_members SET matched_politician_id = dup.keep_id
                    WHERE matched_politician_id = dup.delete_id;
                UPDATE extracted_proposal_judges SET matched_politician_id = dup.keep_id
                    WHERE matched_politician_id = dup.delete_id;

                -- UNIQUE制約があるテーブルは競合行を先に削除してからUPDATE
                -- election_members: UNIQUE(election_id, politician_id)
                DELETE FROM election_members em_del
                    WHERE em_del.politician_id = dup.delete_id
                    AND EXISTS (
                        SELECT 1 FROM election_members em_keep
                        WHERE em_keep.election_id = em_del.election_id
                        AND em_keep.politician_id = dup.keep_id
                    );
                UPDATE election_members SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;

                -- proposal_judge_politicians: UNIQUE(judge_id, politician_id)
                DELETE FROM proposal_judge_politicians pjp_del
                    WHERE pjp_del.politician_id = dup.delete_id
                    AND EXISTS (
                        SELECT 1 FROM proposal_judge_politicians pjp_keep
                        WHERE pjp_keep.judge_id = pjp_del.judge_id
                        AND pjp_keep.politician_id = dup.keep_id
                    );
                UPDATE proposal_judge_politicians SET politician_id = dup.keep_id
                    WHERE politician_id = dup.delete_id;

                -- 重複レコードを削除
                DELETE FROM politicians WHERE id = dup.delete_id;

                RAISE NOTICE 'Merged politician id % into %', dup.delete_id, dup.keep_id;
            END LOOP;
        END $$;
    """)

    # Step 2: name列にUNIQUE制約を追加
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_politicians_name
        ON politicians(name);
    """)


def downgrade() -> None:
    """UNIQUE制約を削除（重複データの復元は不可）."""
    op.execute("""
        DROP INDEX IF EXISTS uq_politicians_name;
    """)
    # 注意: 重複politicianの復元はデータ変更のため不可能
