#!/bin/bash

# Docker Compose環境のセットアップと動作確認用スクリプト

echo "Docker Compose環境をビルドしています..."
docker compose -f docker/docker-compose.yml build

echo "PostgreSQLを含む全サービスを起動しています..."
docker compose -f docker/docker-compose.yml up -d

echo "PostgreSQLの準備完了を待機しています..."
sleep 10

echo "データベース接続をテストしています..."
docker compose -f docker/docker-compose.yml exec sagebase python -m src.infrastructure.config.database

echo "PostgreSQLデータベースの状態を確認しています..."
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db -c "\dt"

echo "テーブル作成状況を確認しています..."
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"

echo "設定完了！以下のコマンドでコンテナにアクセスできます："
echo "docker compose -f docker/docker-compose.yml exec sagebase bash"
echo "docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db"
