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
        "database/seed_political_parties_generated.sql"
        "database/seed_conferences_generated.sql"
        "database/seed_parliamentary_groups_generated.sql"
        "database/seed_parliamentary_group_parties_generated.sql"
        "database/seed_meetings_generated.sql"
        "database/seed_politicians_generated.sql"
        "database/seed_election_members_generated.sql"
        "database/seed_parliamentary_group_memberships_generated.sql"
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
fi
