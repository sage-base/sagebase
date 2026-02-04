#!/bin/bash
# データベース接続テストスクリプト

echo "🏗️  Sagebase データベース接続テスト"
echo "=================================="

# Docker Composeが起動しているかチェック
if ! docker compose -f docker/docker-compose.yml ps postgres | grep -q "Up"; then
    echo "❌ PostgreSQLコンテナが起動していません"
    echo "以下のコマンドでDockerサービスを起動してください："
    echo "docker compose -f docker/docker-compose.yml up -d"
    exit 1
fi

echo "✅ PostgreSQLコンテナが起動中です"

# データベース接続テスト
echo ""
echo "🔍 データベース接続テストを実行中..."
docker compose -f docker/docker-compose.yml exec -T sagebase uv run python -c "
from src.infrastructure.config.database import test_connection
import sys
if test_connection():
    print('✅ データベース接続成功')
    sys.exit(0)
else:
    print('❌ データベース接続失敗')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🗃️  データベース構造を確認中..."
    docker compose -f docker/docker-compose.yml exec -T postgres psql -U sagebase_user -d sagebase_db -c "\dt"

    echo ""
    echo "🎉 セットアップ完了！"
    echo "以下のコマンドでアプリケーションを実行できます："
    echo "- 議事録分割処理: docker compose -f docker/docker-compose.yml exec sagebase uv run python -m src.main"
    echo "- 政治家抽出処理: docker compose -f docker/docker-compose.yml exec sagebase uv run python -m src.main2"
    echo "- テスト実行: docker compose -f docker/docker-compose.yml exec sagebase uv run pytest"
else
    echo ""
    echo "❌ セットアップに失敗しました"
    echo "ログを確認してください: docker compose -f docker/docker-compose.yml logs"
fi
