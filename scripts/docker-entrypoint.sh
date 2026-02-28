#!/bin/bash
# Docker起動時のエントリーポイントスクリプト

# .venvディレクトリが無効な場合は削除して再作成
if [ -d "/app/.venv" ] && ! [ -f "/app/.venv/bin/python" ]; then
    echo "Invalid .venv directory detected, recreating..."
    rm -rf /app/.venv
    cd /app && uv sync --frozen
fi

# マイグレーション + シード読み込み（AUTO_MIGRATE=false で無効化可能）
if [ "${AUTO_MIGRATE:-true}" = "true" ]; then
    echo "🔄 Running database migrations..."
    cd /app && uv run alembic upgrade head 2>&1 || echo "⚠️ Migration skipped (DB might not be ready)"
    echo "✅ Migrations complete!"

    # シードデータ読み込み
    if [ -f "/app/scripts/load-seeds-internal.sh" ]; then
        /app/scripts/load-seeds-internal.sh
    fi
fi

# コマンドを実行
exec "$@"
