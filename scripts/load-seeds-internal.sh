#!/bin/bash
# コンテナ内部からシードデータを読み込むスクリプト
# docker-entrypoint.sh から呼び出される
# load-seeds.sh と同等のロジックだが、docker compose exec ではなく psql 直接接続を使用
set -e

# DATABASE_URL からDB接続情報をパース
DB_URL="${DATABASE_URL:-postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db}"
DB_USER=$(echo "$DB_URL" | sed 's|.*://\([^:]*\):.*|\1|')
DB_PASSWORD=$(echo "$DB_URL" | sed 's|.*://[^:]*:\([^@]*\)@.*|\1|')
DB_HOST=$(echo "$DB_URL" | sed 's|.*@\([^:]*\):.*|\1|')
DB_PORT=$(echo "$DB_URL" | sed 's|.*:\([0-9]*\)/.*|\1|')
DB_NAME=$(echo "$DB_URL" | sed 's|.*/\(.*\)|\1|')

export PGPASSWORD="$DB_PASSWORD"
PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"

# ヘルパー: テーブル行数を取得
psql_count() {
    $PSQL -t -c "$1" 2>/dev/null | tr -d ' ' || echo "0"
}

# ヘルパー: シードファイルを読み込み
load_seed() {
    local seed_file="$1"
    if [ -f "$seed_file" ]; then
        echo "  Loading $seed_file..."
        $PSQL < "$seed_file" > /dev/null 2>&1
    else
        echo "  ⚠️ Seed file not found: $seed_file"
    fi
}

# governing_bodies テーブルが空かチェック（初回起動判定）
GOVERNING_BODIES_COUNT=$(psql_count "SELECT COUNT(*) FROM governing_bodies;")

if [ "$GOVERNING_BODIES_COUNT" = "0" ]; then
    echo "📦 Loading seed data (first run detected)..."

    # 依存関係順にシードファイルを読み込み
    SEED_FILES=(
        "database/seed_governing_bodies_generated.sql"
        "database/seed_elections_generated.sql"
        "database/seed_hoketsu_elections.sql"
        "database/seed_political_parties_generated.sql"
        "database/seed_conferences_generated.sql"
        "database/seed_parliamentary_groups_generated.sql"
        "database/seed_parliamentary_group_parties_generated.sql"
        "database/seed_meetings_generated.sql"
        "database/seed_politicians_generated.sql"
        "database/seed_hoketsu_politicians.sql"
        "database/seed_election_members_generated.sql"
        "database/seed_hoketsu_election_members.sql"
        "database/seed_parliamentary_group_memberships_generated.sql"
        "database/seed_party_membership_history_generated.sql"
        "database/seed_government_officials.sql"
        "database/seed_government_official_speaker_links.sql"
        "database/seed_speakers_generated.sql"
        "database/seed_speaker_politician_links_generated.sql"
        "database/seed_proposals_generated.sql"
        "database/seed_conference_members_generated.sql"
    )

    for seed_file in "${SEED_FILES[@]}"; do
        load_seed "$seed_file"
    done

    echo "✅ Seed data loaded!"
else
    echo "📦 Seed data already exists, checking for missing data..."

    # elections は後から追加されたSEEDのため、個別にチェック
    ELECTIONS_COUNT=$(psql_count "SELECT COUNT(*) FROM elections;")
    if [ "$ELECTIONS_COUNT" = "0" ]; then
        echo "  📦 Elections data missing, loading..."
        load_seed "database/seed_elections_generated.sql"
        echo "  ✅ Elections data loaded!"
    fi

    # election_members は後から追加されたSEEDのため、個別にチェック
    ELECTION_MEMBERS_COUNT=$(psql_count "SELECT COUNT(*) FROM election_members;")
    if [ "$ELECTION_MEMBERS_COUNT" = "0" ]; then
        echo "  📦 Election members data missing, loading..."
        load_seed "database/seed_election_members_generated.sql"
        echo "  ✅ Election members data loaded!"
    fi

    # parliamentary_groups は後から追加されたSEEDのため、個別にチェック
    PG_COUNT=$(psql_count "SELECT COUNT(*) FROM parliamentary_groups;")
    if [ "$PG_COUNT" = "0" ]; then
        echo "  📦 Parliamentary groups data missing, loading..."
        load_seed "database/seed_parliamentary_groups_generated.sql"
        echo "  ✅ Parliamentary groups data loaded!"
    fi

    # parliamentary_group_memberships は後から追加されたSEEDのため、個別にチェック
    PGM_COUNT=$(psql_count "SELECT COUNT(*) FROM parliamentary_group_memberships;")
    if [ "$PGM_COUNT" = "0" ]; then
        echo "  📦 Parliamentary group memberships data missing, loading..."
        load_seed "database/seed_parliamentary_group_memberships_generated.sql"
        echo "  ✅ Parliamentary group memberships data loaded!"
    fi

    # parliamentary_group_parties は後から追加されたSEEDのため、個別にチェック
    PGP_COUNT=$(psql_count "SELECT COUNT(*) FROM parliamentary_group_parties;")
    if [ "$PGP_COUNT" = "0" ]; then
        echo "  📦 Parliamentary group parties data missing, loading..."
        load_seed "database/seed_parliamentary_group_parties_generated.sql"
        echo "  ✅ Parliamentary group parties data loaded!"
    fi

    # party_membership_history は後から追加されたSEEDのため、個別にチェック
    PMH_COUNT=$(psql_count "SELECT COUNT(*) FROM party_membership_history;")
    if [ "$PMH_COUNT" = "0" ]; then
        echo "  📦 Party membership history data missing, loading..."
        load_seed "database/seed_party_membership_history_generated.sql"
        echo "  ✅ Party membership history data loaded!"
    fi

    # government_officials は後から追加されたSEEDのため、個別にチェック
    GO_COUNT=$(psql_count "SELECT COUNT(*) FROM government_officials;")
    if [ "$GO_COUNT" = "0" ]; then
        echo "  📦 Government officials data missing, loading..."
        load_seed "database/seed_government_officials.sql"
        load_seed "database/seed_government_official_speaker_links.sql"
        echo "  ✅ Government officials data loaded!"
    fi

    # 補欠選挙データは ON CONFLICT で安全にスキップされるため常に投入
    echo "  📦 Loading hoketsu (supplementary election) seed data..."
    load_seed "database/seed_hoketsu_politicians.sql"
    load_seed "database/seed_hoketsu_elections.sql"
    load_seed "database/seed_hoketsu_election_members.sql"
    echo "  ✅ Hoketsu seed data loaded!"

    # speakers は後から追加されたSEEDのため、個別にチェック
    SPEAKERS_COUNT=$(psql_count "SELECT COUNT(*) FROM speakers;")
    if [ "$SPEAKERS_COUNT" = "0" ]; then
        echo "  📦 Speakers data missing, loading..."
        load_seed "database/seed_speakers_generated.sql"
        load_seed "database/seed_speaker_politician_links_generated.sql"
        echo "  ✅ Speakers data loaded!"
    fi

    # speaker_politician_links は UPDATE WHERE 方式で冪等なため、speakersが存在する場合は常に投入
    if [ "$SPEAKERS_COUNT" != "0" ]; then
        echo "  📦 Updating speaker-politician links..."
        load_seed "database/seed_speaker_politician_links_generated.sql"
        echo "  ✅ Speaker-politician links updated!"
    fi

    # proposals は後から追加されたSEEDのため、個別にチェック
    PROPOSALS_COUNT=$(psql_count "SELECT COUNT(*) FROM proposals;")
    if [ "$PROPOSALS_COUNT" = "0" ]; then
        echo "  📦 Proposals data missing, loading..."
        load_seed "database/seed_proposals_generated.sql"
        echo "  ✅ Proposals data loaded!"
    fi

    # conference_members は後から追加されたSEEDのため、個別にチェック
    CM_COUNT=$(psql_count "SELECT COUNT(*) FROM conference_members;")
    if [ "$CM_COUNT" = "0" ]; then
        echo "  📦 Conference members data missing, loading..."
        load_seed "database/seed_conference_members_generated.sql"
        echo "  ✅ Conference members data loaded!"
    fi
fi
