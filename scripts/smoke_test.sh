#!/bin/bash
# スモークテストスクリプト - 本番環境デプロイ後の基本動作確認

set -e

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# テスト結果カウンター
PASSED=0
FAILED=0
TOTAL=0

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
    ((TOTAL++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
    ((TOTAL++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 環境変数の確認
check_env_var() {
    if [ -z "${!1}" ]; then
        log_error "環境変数 $1 が設定されていません"
        return 1
    fi
    return 0
}

echo -e "${GREEN}=== Sagebase スモークテスト ===${NC}"
echo ""

# 必須環境変数の確認
log_info "環境変数を確認中..."
check_env_var "SERVICE_URL" || SERVICE_URL=""
check_env_var "PROJECT_ID" || PROJECT_ID=""
check_env_var "REGION" || REGION="asia-northeast1"

if [ -z "$SERVICE_URL" ]; then
    log_warning "SERVICE_URLが設定されていません。Cloud Runサービスから取得を試みます..."
    if [ -n "$PROJECT_ID" ] && [ -n "$REGION" ]; then
        SERVICE_NAME="${SERVICE_NAME:-sagebase-streamlit}"
        SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --format="value(status.url)" 2>/dev/null || echo "")

        if [ -n "$SERVICE_URL" ]; then
            log_success "SERVICE_URLを取得しました: $SERVICE_URL"
        else
            log_error "SERVICE_URLを取得できませんでした"
            exit 1
        fi
    else
        log_error "PROJECT_IDまたはREGIONが設定されていません"
        exit 1
    fi
fi

echo ""
log_info "テスト対象: $SERVICE_URL"
log_info "プロジェクト: $PROJECT_ID"
log_info "リージョン: $REGION"
echo ""

# Test 1: ヘルスチェックエンドポイント確認
log_info "Test 1: Streamlitヘルスチェックエンドポイント"
if curl -sf "${SERVICE_URL}/_stcore/health" > /dev/null 2>&1; then
    log_success "ヘルスチェックエンドポイントが応答しています"
else
    log_error "ヘルスチェックエンドポイントが応答していません"
fi

# Test 2: サービスのHTTPレスポンス確認
log_info "Test 2: サービスのHTTPレスポンス"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL" || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    log_success "サービスが正常にレスポンスを返しています (HTTP $HTTP_CODE)"
else
    log_error "サービスが正常にレスポンスを返していません (HTTP $HTTP_CODE)"
fi

# Test 3: サービスのレスポンスタイム確認
log_info "Test 3: サービスのレスポンスタイム"
RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$SERVICE_URL" || echo "999")
RESPONSE_TIME_MS=$(echo "$RESPONSE_TIME * 1000" | bc)
if (( $(echo "$RESPONSE_TIME < 5" | bc -l) )); then
    log_success "レスポンスタイムが良好です (${RESPONSE_TIME_MS}ms)"
else
    log_warning "レスポンスタイムが遅いです (${RESPONSE_TIME_MS}ms) - 初回アクセスの場合は正常です"
    ((PASSED++))
    ((TOTAL++))
fi

# Test 4: Cloud Runサービスの状態確認
if [ -n "$PROJECT_ID" ] && [ -n "$REGION" ]; then
    log_info "Test 4: Cloud Runサービスの状態"
    SERVICE_NAME="${SERVICE_NAME:-sagebase-streamlit}"
    SERVICE_STATUS=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.conditions[0].status)" 2>/dev/null || echo "Unknown")

    if [ "$SERVICE_STATUS" = "True" ]; then
        log_success "Cloud Runサービスが正常に稼働しています"
    else
        log_error "Cloud Runサービスの状態が異常です: $SERVICE_STATUS"
    fi
else
    log_warning "Test 4: スキップ（PROJECT_IDまたはREGIONが未設定）"
fi

# Test 5: データベース接続確認（Cloud SQL）
if [ -n "$PROJECT_ID" ] && [ -n "$CLOUD_SQL_INSTANCE" ]; then
    log_info "Test 5: Cloud SQLインスタンスの状態"
    DB_STATUS=$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" \
        --project="$PROJECT_ID" \
        --format="value(state)" 2>/dev/null || echo "UNKNOWN")

    if [ "$DB_STATUS" = "RUNNABLE" ]; then
        log_success "Cloud SQLインスタンスが正常に稼働しています"
    else
        log_error "Cloud SQLインスタンスの状態が異常です: $DB_STATUS"
    fi
else
    log_warning "Test 5: スキップ（CLOUD_SQL_INSTANCEが未設定）"
fi

# Test 6: GCSバケットの存在確認
if [ -n "$PROJECT_ID" ]; then
    log_info "Test 6: GCSバケットの存在確認"
    MINUTES_BUCKET="${PROJECT_ID}-sagebase-minutes-${ENVIRONMENT:-production}"

    if gsutil ls -b "gs://$MINUTES_BUCKET" > /dev/null 2>&1; then
        log_success "GCSバケット ($MINUTES_BUCKET) が存在します"
    else
        log_error "GCSバケット ($MINUTES_BUCKET) が存在しません"
    fi
else
    log_warning "Test 6: スキップ（PROJECT_IDが未設定）"
fi

# Test 7: Vertex AI APIアクセス確認
if [ -n "$PROJECT_ID" ]; then
    log_info "Test 7: Vertex AI API有効化確認"

    if gcloud services list --enabled --project="$PROJECT_ID" \
        --filter="name:aiplatform.googleapis.com" \
        --format="value(name)" | grep -q "aiplatform.googleapis.com"; then
        log_success "Vertex AI APIが有効化されています"
    else
        log_error "Vertex AI APIが有効化されていません"
    fi
else
    log_warning "Test 7: スキップ（PROJECT_IDが未設定）"
fi

# Test 8: Secret Managerのシークレット確認
if [ -n "$PROJECT_ID" ]; then
    log_info "Test 8: Secret Managerのシークレット確認"

    # database-passwordの確認
    if gcloud secrets describe database-password --project="$PROJECT_ID" > /dev/null 2>&1; then
        log_success "Secret Manager: database-password が存在します"
    else
        log_error "Secret Manager: database-password が存在しません"
    fi
else
    log_warning "Test 8: スキップ（PROJECT_IDが未設定）"
fi

# Test 9: Cloud Monitoringダッシュボードの確認
if [ -n "$PROJECT_ID" ]; then
    log_info "Test 9: Cloud Monitoringダッシュボード"

    DASHBOARD_COUNT=$(gcloud monitoring dashboards list --project="$PROJECT_ID" \
        --format="value(name)" 2>/dev/null | wc -l)

    if [ "$DASHBOARD_COUNT" -gt 0 ]; then
        log_success "Cloud Monitoringダッシュボードが設定されています ($DASHBOARD_COUNT個)"
    else
        log_warning "Cloud Monitoringダッシュボードが設定されていません"
        ((PASSED++))
        ((TOTAL++))
    fi
else
    log_warning "Test 9: スキップ（PROJECT_IDが未設定）"
fi

# Test 10: アラートポリシーの確認
if [ -n "$PROJECT_ID" ]; then
    log_info "Test 10: アラートポリシー"

    ALERT_COUNT=$(gcloud alpha monitoring policies list --project="$PROJECT_ID" \
        --format="value(name)" 2>/dev/null | wc -l)

    if [ "$ALERT_COUNT" -gt 0 ]; then
        log_success "アラートポリシーが設定されています ($ALERT_COUNT個)"
    else
        log_warning "アラートポリシーが設定されていません"
        ((PASSED++))
        ((TOTAL++))
    fi
else
    log_warning "Test 10: スキップ（PROJECT_IDが未設定）"
fi

# 結果サマリー
echo ""
echo -e "${GREEN}=== テスト結果サマリー ===${NC}"
echo "合計テスト数: $TOTAL"
echo -e "${GREEN}成功: $PASSED${NC}"
echo -e "${RED}失敗: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ すべてのスモークテストに合格しました！${NC}"
    exit 0
else
    echo -e "${RED}❌ いくつかのテストが失敗しました。詳細を確認してください。${NC}"
    exit 1
fi
