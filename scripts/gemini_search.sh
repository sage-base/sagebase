#!/usr/bin/env bash
# gemini-cliを使ったGoogle検索ヘルパー
# 使い方: ./scripts/gemini_search.sh "検索クエリ"
#
# 例:
#   ./scripts/gemini_search.sh "高市早苗 所属政党 2026年"
#   ./scripts/gemini_search.sh "東京都議会 議長 現在"
#
# 必要な環境変数: GOOGLE_API_KEY（.envに設定済み）

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "使い方: $0 \"検索クエリ\"" >&2
    exit 1
fi

QUERY="$1"

# .envからAPIキーを読み込む（未設定の場合）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
if [ -z "${GOOGLE_API_KEY:-}" ] && [ -f "$PROJECT_ROOT/.env" ]; then
    export "$(grep '^GOOGLE_API_KEY=' "$PROJECT_ROOT/.env" | head -1)"
fi

# gemini-cliの存在確認
if ! command -v gemini &> /dev/null; then
    echo "エラー: gemini-cli がインストールされていません" >&2
    echo "インストール: npm install -g @google/gemini-cli" >&2
    exit 1
fi

# 検索用のシステムプロンプト
SEARCH_PROMPT="あなたはファクトチェッカーです。以下の質問について、Google検索で最新の情報を調べて、正確に回答してください。
情報源がある場合はURLも含めてください。不確実な情報には「未確認」と明記してください。

質問: ${QUERY}"

gemini -p "$SEARCH_PROMPT" --model "${GEMINI_MODEL:-gemini-2.0-flash}" --output-format text -y 2>&1 | grep -v "^Both GOOGLE_API_KEY" | grep -v "^YOLO mode"
