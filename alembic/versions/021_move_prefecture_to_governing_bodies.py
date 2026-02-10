"""都道府県(prefecture)をconferencesからgoverning_bodiesへ移行.

Revision ID: 021
Revises: 020
Create Date: 2026-02-10

都道府県は会議体ではなく開催主体の属性であるため、
governing_bodiesテーブルにprefectureカラムを追加し、
conferencesテーブルからprefectureカラムを削除する。

データ移行:
- organization_codeの先頭2桁からJIS都道府県コードで都道府県名をマッピング
- type='国' → NULL
- organization_code NULL → NULL
"""

from alembic import op


revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration: Move prefecture from conferences to governing_bodies."""
    op.execute("""
        ALTER TABLE governing_bodies
        ADD COLUMN IF NOT EXISTS prefecture VARCHAR(10);

        CREATE INDEX IF NOT EXISTS idx_governing_bodies_prefecture
        ON governing_bodies(prefecture);

        UPDATE governing_bodies
        SET prefecture = CASE
            WHEN type = '国' THEN NULL
            WHEN organization_code IS NULL THEN NULL
            ELSE CASE LEFT(organization_code, 2)
                WHEN '01' THEN '北海道'
                WHEN '02' THEN '青森県'
                WHEN '03' THEN '岩手県'
                WHEN '04' THEN '宮城県'
                WHEN '05' THEN '秋田県'
                WHEN '06' THEN '山形県'
                WHEN '07' THEN '福島県'
                WHEN '08' THEN '茨城県'
                WHEN '09' THEN '栃木県'
                WHEN '10' THEN '群馬県'
                WHEN '11' THEN '埼玉県'
                WHEN '12' THEN '千葉県'
                WHEN '13' THEN '東京都'
                WHEN '14' THEN '神奈川県'
                WHEN '15' THEN '新潟県'
                WHEN '16' THEN '富山県'
                WHEN '17' THEN '石川県'
                WHEN '18' THEN '福井県'
                WHEN '19' THEN '山梨県'
                WHEN '20' THEN '長野県'
                WHEN '21' THEN '岐阜県'
                WHEN '22' THEN '静岡県'
                WHEN '23' THEN '愛知県'
                WHEN '24' THEN '三重県'
                WHEN '25' THEN '滋賀県'
                WHEN '26' THEN '京都府'
                WHEN '27' THEN '大阪府'
                WHEN '28' THEN '兵庫県'
                WHEN '29' THEN '奈良県'
                WHEN '30' THEN '和歌山県'
                WHEN '31' THEN '鳥取県'
                WHEN '32' THEN '島根県'
                WHEN '33' THEN '岡山県'
                WHEN '34' THEN '広島県'
                WHEN '35' THEN '山口県'
                WHEN '36' THEN '徳島県'
                WHEN '37' THEN '香川県'
                WHEN '38' THEN '愛媛県'
                WHEN '39' THEN '高知県'
                WHEN '40' THEN '福岡県'
                WHEN '41' THEN '佐賀県'
                WHEN '42' THEN '長崎県'
                WHEN '43' THEN '熊本県'
                WHEN '44' THEN '大分県'
                WHEN '45' THEN '宮崎県'
                WHEN '46' THEN '鹿児島県'
                WHEN '47' THEN '沖縄県'
                ELSE NULL
            END
        END;

        ALTER TABLE conferences
        DROP COLUMN IF EXISTS prefecture;

        DROP INDEX IF EXISTS idx_conferences_prefecture;
    """)


def downgrade() -> None:
    """Rollback migration: Move prefecture back from governing_bodies to conferences."""
    op.execute("""
        ALTER TABLE conferences
        ADD COLUMN IF NOT EXISTS prefecture VARCHAR(10);

        CREATE INDEX IF NOT EXISTS idx_conferences_prefecture
        ON conferences(prefecture);

        UPDATE conferences c
        SET prefecture = gb.prefecture
        FROM governing_bodies gb
        WHERE c.governing_body_id = gb.id;

        ALTER TABLE governing_bodies
        DROP COLUMN IF EXISTS prefecture;

        DROP INDEX IF EXISTS idx_governing_bodies_prefecture;
    """)
