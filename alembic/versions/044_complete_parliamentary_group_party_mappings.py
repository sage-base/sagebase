"""会派⇔政党マッピング残り12件の100%化.

Revision ID: 044
Revises: 043
Create Date: 2026-03-25

未マッピング12会派（京都市会3件、衆議院active2件、衆議院inactive7件）に
対して政党マッピングを追加し、カバレッジを90%→100%にする。

- 京都市会: 改新京都、民主・市民フォーラム京都市会議員団、維新・京都・国民市会議員団
- 衆議院active: 改革の会、有志の会
- 衆議院inactive: 21世紀クラブ、国益と国民の生活を守る会、改革無所属の会、
  改革結集の会、未来日本、社会保障を立て直す国民会議、２１世紀

id:81（21世紀クラブ, 2000-2001）とid:134（２１世紀, 1996-2000）は
期間が異なる別会派であることを確認。重複ではない。

関連: Issue #1403
"""

from alembic import op


revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """未マッピング12会派の政党マッピングを追加する."""
    # ================================================================
    # Phase 1: 不足する政党の追加
    # ================================================================
    op.execute("""
        INSERT INTO political_parties (name) VALUES
            ('京都党')
        ON CONFLICT (name) DO NOTHING;
    """)

    # ================================================================
    # Phase 2: 京都市会 - 3会派のPrimaryマッピング追加
    # ================================================================

    # 改新京都 → 立憲民主党（片桐直哉=立憲、小島信太郎=国民民主の超党派会派）
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, true
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        CROSS JOIN political_parties pp
        WHERE gb.name = '京都府京都市' AND gb.type = '市町村'
          AND pg.name = '改新京都'
          AND pp.name = '立憲民主党'
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # 改新京都 → 国民民主党（Secondary）
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, false
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        CROSS JOIN political_parties pp
        WHERE gb.name = '京都府京都市' AND gb.type = '市町村'
          AND pg.name = '改新京都'
          AND pp.name = '国民民主党'
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # 民主・市民フォーラム京都市会議員団 → 立憲民主党
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, true
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        CROSS JOIN political_parties pp
        WHERE gb.name = '京都府京都市' AND gb.type = '市町村'
          AND pg.name = '民主・市民フォーラム京都市会議員団'
          AND pp.name = '立憲民主党'
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # 維新・京都・国民市会議員団 → 日本維新の会（Primary）
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, true
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        CROSS JOIN political_parties pp
        WHERE gb.name = '京都府京都市' AND gb.type = '市町村'
          AND pg.name = '維新・京都・国民市会議員団'
          AND pp.name = '日本維新の会'
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # 維新・京都・国民市会議員団 → 京都党（Secondary）
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, false
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        CROSS JOIN political_parties pp
        WHERE gb.name = '京都府京都市' AND gb.type = '市町村'
          AND pg.name = '維新・京都・国民市会議員団'
          AND pp.name = '京都党'
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # 維新・京都・国民市会議員団 → 国民民主党（Secondary）
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, false
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        CROSS JOIN political_parties pp
        WHERE gb.name = '京都府京都市' AND gb.type = '市町村'
          AND pg.name = '維新・京都・国民市会議員団'
          AND pp.name = '国民民主党'
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # ================================================================
    # Phase 3: 衆議院active - 2会派のPrimaryマッピング追加
    # ================================================================
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, true
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        JOIN (VALUES
            ('改革の会', '無所属'),
            ('有志の会', '無所属')
        ) AS tmp(group_name, party_name) ON pg.name = tmp.group_name
        JOIN political_parties pp ON pp.name = tmp.party_name
        WHERE gb.name = '国会' AND gb.type = '国'
          AND pg.chamber = '衆議院'
          AND pg.is_active = true
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # ================================================================
    # Phase 4: 衆議院inactive - 7会派のPrimaryマッピング追加
    # ================================================================
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, true
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        JOIN (VALUES
            ('21世紀クラブ', '無所属'),
            ('国益と国民の生活を守る会', '無所属'),
            ('改革無所属の会', '無所属'),
            ('改革結集の会', '無所属'),
            ('未来日本', '無所属'),
            ('社会保障を立て直す国民会議', '無所属'),
            ('２１世紀', '無所属')
        ) AS tmp(group_name, party_name) ON pg.name = tmp.group_name
        JOIN political_parties pp ON pp.name = tmp.party_name
        WHERE gb.name = '国会' AND gb.type = '国'
          AND pg.chamber = '衆議院'
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)


def downgrade() -> None:
    """ロールバック: データ投入のみのため空実装.

    具体的なロールバックが必要な場合は、
    parliamentary_group_parties テーブルから該当レコードを手動削除する。
    """
    pass
