#!/bin/bash
# Load seed data into the database
# This script is run after Alembic migrations to populate initial data
#
# Usage: ./scripts/load-seeds.sh [compose_cmd]
# Example: ./scripts/load-seeds.sh "-f docker/docker-compose.yml"

set -e

COMPOSE_CMD="${1:--f docker/docker-compose.yml}"

# Helper: execute psql query and return trimmed result
psql_count() {
    docker compose $COMPOSE_CMD exec -T postgres psql -U sagebase_user -d sagebase_db -t -c "$1" 2>/dev/null | tr -d ' ' || echo "0"
}

# Helper: load a seed file
load_seed() {
    local seed_file="$1"
    if [ -f "$seed_file" ]; then
        echo "  Loading $seed_file..."
        docker compose $COMPOSE_CMD exec -T postgres psql -U sagebase_user -d sagebase_db < "$seed_file" > /dev/null 2>&1
    else
        echo "  ⚠️ Seed file not found: $seed_file"
    fi
}

# Check if governing_bodies table is empty (indicates first run)
GOVERNING_BODIES_COUNT=$(psql_count "SELECT COUNT(*) FROM governing_bodies;")

if [ "$GOVERNING_BODIES_COUNT" = "0" ]; then
    echo "📦 Loading seed data (first run detected)..."

    # Load seeds in order (dependencies matter)
    SEED_FILES=(
        "database/seed_governing_bodies_generated.sql"
        "database/seed_elections_generated.sql"
        "database/seed_political_parties_generated.sql"
        "database/seed_conferences_generated.sql"
        "database/seed_parliamentary_groups_generated.sql"
        "database/seed_parliamentary_group_parties_generated.sql"
        "database/seed_meetings_generated.sql"
        "database/seed_politicians_generated.sql"
        "database/seed_election_members_generated.sql"
        "database/seed_parliamentary_group_memberships_generated.sql"
        "database/seed_party_membership_history_generated.sql"
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
fi
