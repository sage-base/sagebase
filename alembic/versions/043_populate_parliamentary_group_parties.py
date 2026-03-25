"""会派⇔政党マッピング（parliamentary_group_parties）のデータ補完.

Revision ID: 043
Revises: 042
Create Date: 2026-03-25

88会派中31グループ（35%カバレッジ）→ 約73グループ（90%カバレッジ）に改善。
未マッピングの会派に対して、政党名ベースのPrimaryマッピングを追加する。
必要に応じて不足する歴史的政党もpolitical_partiesに追加する。

関連: Issue #1390
"""

from alembic import op


revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """会派⇔政党マッピングを補完する."""
    # ================================================================
    # Phase 1: 不足する政党の追加（最小限）
    # 選挙インポートで作成済みの場合はON CONFLICTでスキップ
    # ================================================================
    op.execute("""
        INSERT INTO political_parties (name) VALUES
            ('沖縄の風'),
            ('おおさか維新の会'),
            ('みんなの党'),
            ('保守新党'),
            ('たちあがれ日本'),
            ('次世代の党'),
            ('結いの党'),
            ('維新の党'),
            ('自由党'),
            ('新進党'),
            ('太陽党'),
            ('新党さきがけ'),
            ('生活の党'),
            ('国民の生活が第一'),
            ('民進党')
        ON CONFLICT (name) DO NOTHING;
    """)

    # ================================================================
    # Phase 2: 衆議院active - 未マッピング会派のPrimary追加
    # ================================================================
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, true
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        JOIN (VALUES
            ('日本保守党', '日本保守党'),
            ('無所属', '無所属')
        ) AS tmp(group_name, party_name) ON pg.name = tmp.group_name
        JOIN political_parties pp ON pp.name = tmp.party_name
        WHERE gb.name = '国会' AND gb.type = '国'
          AND pg.chamber = '衆議院'
          AND pg.is_active = true
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # ================================================================
    # Phase 3: 参議院active - 未マッピング会派のPrimary追加
    # ================================================================
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, true
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        JOIN (VALUES
            ('国民民主党・新緑風会', '国民民主党'),
            ('沖縄の風', '沖縄の風'),
            ('社会民主党', '社会民主党'),
            ('立憲民主・無所属', '立憲民主党'),
            ('各派に属しない議員', '無所属')
        ) AS tmp(group_name, party_name) ON pg.name = tmp.group_name
        JOIN political_parties pp ON pp.name = tmp.party_name
        WHERE gb.name = '国会' AND gb.type = '国'
          AND pg.chamber = '参議院'
        ON CONFLICT (parliamentary_group_id, political_party_id) DO NOTHING;
    """)

    # ================================================================
    # Phase 4: 衆議院inactive - 未マッピング会派のPrimary追加
    # KNOWN_PARTY_MAPPINGS (investigate_kaiha_mapping.py) に準拠
    # ================================================================
    op.execute("""
        INSERT INTO parliamentary_group_parties
            (parliamentary_group_id, political_party_id, is_primary)
        SELECT pg.id, pp.id, true
        FROM parliamentary_groups pg
        JOIN governing_bodies gb ON pg.governing_body_id = gb.id
        JOIN (VALUES
            -- 完全一致系
            ('たちあがれ日本', 'たちあがれ日本'),
            ('みんなの党', 'みんなの党'),
            ('保守党', '保守党'),
            ('保守新党', '保守新党'),
            ('国民新党', '国民新党'),
            ('太陽党', '太陽党'),
            ('希望の党', '希望の党'),
            ('新党きづな', '新党きづな'),
            ('新党さきがけ', '新党さきがけ'),
            ('新進党', '新進党'),
            ('日本維新の会', '日本維新の会'),
            ('次世代の党', '次世代の党'),
            ('民主党', '民主党'),
            ('結いの党', '結いの党'),
            ('自由党', '自由党'),
            ('自由民主党', '自由民主党'),
            ('生活の党', '生活の党'),
            -- 略称→正式名系
            ('さきがけ', '新党さきがけ'),
            ('おおさか維新の会', '日本維新の会'),
            ('維新の党', '日本維新の会'),
            -- 連立会派のPrimary政党
            ('国民新党・そうぞう・無所属の会', '国民新党'),
            ('国民新党・大地・無所属の会', '国民新党'),
            ('国民新党・新党日本', '国民新党'),
            ('国民新党・日本・無所属の会', '国民新党'),
            ('国民新党・無所属の会', '国民新党'),
            ('国民新党・無所属会', '国民新党'),
            ('国民の生活が第一・きづな', '国民の生活が第一'),
            ('希望の党・無所属クラブ', '希望の党'),
            ('平和・改革', '公明党'),
            ('公明党・改革クラブ', '公明党'),
            ('新党大地・真民主', '新党大地'),
            ('日本維新の会・無所属の会', '日本維新の会'),
            ('民主・維新・無所属クラブ', '民主党'),
            ('民主党・無所属クラブ', '民主党'),
            ('民主党・無所属クラブ・国民新党', '民主党'),
            ('民友連', '民主党'),
            ('民進党・無所属クラブ', '民進党'),
            ('減税日本・平安', '減税日本'),
            ('無所属の会', '無所属'),
            ('生活の党と山本太郎となかまたち', '生活の党'),
            ('社会民主党・市民連合', '社会民主党'),
            ('立憲民主・国民・社保・無所属フォーラム', '立憲民主党'),
            ('立憲民主党・市民クラブ', '立憲民主党'),
            ('立憲民主党・無所属フォーラム', '立憲民主党'),
            ('立憲民主党・社民・無所属', '立憲民主党'),
            ('自由民主党・改革クラブ', '自由民主党'),
            ('自由民主党・無所属会', '自由民主党')
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
