#!/bin/bash
# PostgreSQLデータベースリセットスクリプト

echo "🗑️  Sagebase データベースリセット"
echo "=================================="

# 確認メッセージ
echo "⚠️  注意: この操作は以下を実行します:"
echo "   - PostgreSQLコンテナを停止"
echo "   - データベースボリュームを削除 (全データが失われます)"
echo "   - コンテナを再作成してデータベースを初期化"
echo ""
read -p "本当に実行しますか？ (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 操作をキャンセルしました"
    exit 0
fi

echo ""
echo "🛑 PostgreSQLコンテナを停止中..."
docker compose -f docker/docker-compose.yml stop postgres

echo "🗑️  データベースボリュームを削除中..."
docker compose -f docker/docker-compose.yml down -v

echo "🚀 コンテナを再作成中..."
docker compose -f docker/docker-compose.yml up -d postgres

echo "⏳ PostgreSQLの起動を待機中..."

# 最大待機時間（60秒）
MAX_WAIT=60
WAIT_COUNT=0

# 初期化が完了するまで少し待機
sleep 5

# PostgreSQLコンテナの状態確認
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # コンテナが実行中か確認（docker psを使用）
    if ! docker ps | grep -q "docker-postgres-1"; then
        # コンテナが存在しない、または停止している
        echo "   ❌ PostgreSQLコンテナが見つかりません、または異常終了しました"
        echo "   コンテナの状態:"
        docker ps -a | grep postgres || echo "PostgreSQLコンテナが見つかりません"
        echo ""
        echo "   最後のログ:"
        docker logs docker-postgres-1 --tail 50 2>&1 || echo "ログが取得できません"
        exit 1
    fi

    # pg_isreadyでPostgreSQLの準備状態を確認
    if docker exec docker-postgres-1 pg_isready -U sagebase_user -d sagebase_db > /dev/null 2>&1; then
        echo "✅ PostgreSQLが起動しました"
        break
    fi

    echo "   PostgreSQL起動待機中... ($((WAIT_COUNT+1))/$MAX_WAIT 秒)"
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT+1))
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "❌ PostgreSQLの起動がタイムアウトしました"
    echo "最後のログ:"
    docker logs docker-postgres-1 --tail 50 2>&1
    exit 1
fi

echo ""
echo "🔍 データベース初期化状態を確認中..."
echo ""
echo "📋 テーブル一覧:"
docker exec docker-postgres-1 psql -U sagebase_user -d sagebase_db -c "\dt" | grep -E "public|meetings|conferences|politicians|speakers|conversations|proposals|governing_bodies|political_parties|parliamentary_groups|extracted_conference_members|conference_members"

echo ""
echo "🔄 マイグレーション実行状況を確認中..."
echo ""
echo "meetings テーブルのカラム確認:"
docker exec docker-postgres-1 psql -U sagebase_user -d sagebase_db -c "\d meetings" | grep -E "gcs_pdf_uri|gcs_text_uri|url|name|processed_at" || echo "  ✅ meetings テーブルのマイグレーション確認完了"

echo ""
echo "conferences テーブルのカラム確認:"
docker exec docker-postgres-1 psql -U sagebase_user -d sagebase_db -c "\d conferences" | grep "members_introduction_url" || echo "  ✅ conferences テーブルのマイグレーション確認完了"

echo ""
echo "🎉 データベースリセット完了！"
echo ""
echo "📊 初期データが設定されています："
echo "統治機関 (governing_bodies):"
docker exec docker-postgres-1 psql -U sagebase_user -d sagebase_db -t -c "SELECT COUNT(*) as count, type FROM governing_bodies GROUP BY type ORDER BY type;" | grep -v "^$"

echo ""
echo "政党 (political_parties):"
docker exec docker-postgres-1 psql -U sagebase_user -d sagebase_db -t -c "SELECT name FROM political_parties ORDER BY name;" | head -5
echo "... (他の政党は省略)"

echo ""
echo "会議 (conferences):"
docker exec docker-postgres-1 psql -U sagebase_user -d sagebase_db -t -c "SELECT COUNT(*) FROM conferences;" | tr -d ' '
echo "件の会議データ"

echo ""
echo "📝 次のステップ:"
echo "   - アプリケーションを起動: docker compose -f docker/docker-compose.yml up -d"
echo "   - セットアップテスト: ./test-setup.sh"
echo ""
echo "⚠️  注意: PostgreSQLの初期化時に、Alembicマイグレーションが自動実行されます"
echo "   データの投入は以下のコマンドで行ってください:"
echo "   just restore-latest"
