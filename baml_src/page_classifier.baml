// Page Classification for Sagebase
// ページ分類用のBAML定義

// ========================================
// Class Definitions (Pydanticモデルに対応)
// ========================================

// PageClassification - ページタイプの分類結果
class PageClassification {
    page_type string @description("Type of page: index_page, member_list_page, other")
    confidence float @description("Confidence score (0.0-1.0)")
    reason string @description("Reason for classification")
    has_child_links bool @description("Whether the page has child links")
    has_member_info bool @description("Whether the page has member information")
}

// ========================================
// Function Definitions
// ========================================

// Function: ページを分類
function ClassifyPage(
    html_excerpt: string,
    current_url: string,
    party_name: string
) -> PageClassification {
    client Gemini2Flash
    prompt #"
        以下のWebページを分類してください。

        URL: {{ current_url }}
        政党名: {{ party_name }}

        HTMLの一部（抜粋）:
        {{ html_excerpt }}

        タスク:
        このページを以下のタイプに分類してください:
        - index_page: インデックスページ（他のページへのリンク集、ナビゲーションページ）
        - member_list_page: 議員一覧ページ（議員の情報が掲載されているページ）
        - other: その他のページ

        指示:
        1. HTMLの内容から適切なページタイプを判定してください
        2. has_child_links: このページに子ページへのリンクがあるかを判定（true/false）
        3. has_member_info: このページに議員情報が含まれているかを判定（true/false）
        4. confidence: 分類の確信度を0.0-1.0で表してください
        5. reason: 判定理由を簡潔に説明してください（日本語で）

        判定のポイント:
        - インデックスページ: 「都道府県一覧」「支部一覧」「地域別」などのナビゲーションリンクが多い
        - 議員一覧ページ: 議員名、役職、連絡先、プロフィールなどの情報が複数含まれている
        - その他: 上記に該当しない一般的なページ

        注意:
        - URLやHTMLの構造から総合的に判断してください
        - 政党名も判定の参考にしてください
        - HTMLは抜粋なので、完全な情報がない場合もあります

        出力形式（JSON）:
        {
          "page_type": "index_page",
          "confidence": 0.92,
          "reason": "「都道府県別」「支部一覧」などのナビゲーションリンクが多数含まれているため、インデックスページと判断",
          "has_child_links": true,
          "has_member_info": false
        }
    "#
}
