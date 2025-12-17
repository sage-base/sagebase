// Link Classification for Sagebase
// リンク分類用のBAML定義

// ========================================
// Class Definitions (Pydanticモデルに対応)
// ========================================

// LinkClassification - 個別リンクの分類結果
class LinkClassification {
    url string @description("The URL being classified")
    link_type string @description("Type of link: prefecture_list, city_list, member_list, member_profile, other")
    confidence float @description("Confidence score (0.0-1.0)")
    reason string @description("Reason for classification")
}

// ========================================
// Function Definitions
// ========================================

// Function: リンクを分類
function ClassifyLinks(
    links: string,
    party_name: string,
    context: string
) -> LinkClassification[] {
    client Gemini2Flash
    prompt #"
        以下のリンクを分類してください。

        リンク情報:
        {{ links }}

        政党名: {{ party_name }}
        コンテキスト: {{ context }}

        タスク:
        各リンクを以下のタイプに分類してください:
        - prefecture_list: 都道府県別リスト（例: 「北海道」「東京都」などのリンク）
        - city_list: 市区町村別リスト（例: 「札幌市」「渋谷区」などのリンク）
        - member_list: 議員一覧ページ（例: 「議員一覧」「メンバー紹介」などのリンク）
        - member_profile: 議員個人ページ（例: 個別の議員名のリンク）
        - other: その他のリンク

        指示:
        1. 各リンクのURL、テキスト、タイトルから適切なタイプを判定してください
        2. URLは元のリンク情報から正確に抽出してください（改変しない）
        3. confidenceは分類の確信度を0.0-1.0で表してください
        4. reasonには判定理由を簡潔に説明してください（日本語で）

        注意:
        - URLは必ずリンク情報に含まれているものをそのまま使用してください
        - リンクのテキストやタイトルが分類の重要な手がかりになります
        - 政党名やコンテキストも考慮して分類してください

        出力形式（JSON配列）:
        [
          {
            "url": "https://example.com/link1",
            "link_type": "member_list",
            "confidence": 0.95,
            "reason": "「議員一覧」というテキストから議員リストページと判断"
          },
          {
            "url": "https://example.com/link2",
            "link_type": "prefecture_list",
            "confidence": 0.88,
            "reason": "「北海道」というテキストから都道府県リストと判断"
          }
        ]
    "#
}
