// Role Name Mapping for Sagebase
// 役職-人名マッピング抽出用のBAML定義

// ========================================
// Class Definitions
// ========================================

// 役職と人名のマッピング
class RoleNameMapping {
    role string @description("役職名（例: 議長、副議長、知事、委員長）")
    name string @description("人名（例: 伊藤条一、梶谷大志）。敬称は除外すること")
    member_number string? @description("議員番号（あれば。例: 100番、82番）")
}

// 役職-人名マッピング抽出結果
class RoleNameMappingResult {
    mappings RoleNameMapping[] @description("役職と人名のマッピングリスト")
    attendee_section_found bool @description("出席者セクションが見つかったか")
    confidence float @description("抽出の信頼度（0.0-1.0）")
}

// ========================================
// Function Definitions
// ========================================

// 出席者情報から役職-人名マッピングを抽出
function ExtractRoleNameMapping(
    attendee_text: string
) -> RoleNameMappingResult {
    client Gemini2Flash
    prompt #"
        以下の議事録の出席者情報から、役職と人名の対応を抽出してください。

        出席者情報:
        {{ attendee_text }}

        # 抽出対象
        1. 役職名（議長、副議長、知事、副知事、委員長、副委員長など）
        2. その役職に対応する人名（敬称は除外）
        3. 議員番号（記載がある場合のみ）

        # 注意事項
        - 人名は姓名を正確に抽出してください
        - 敬称（議員、氏、さん、様、先生、君など）は除外してください
        - 役職のない一般出席者は含めないでください
        - 「出席議員」セクション全体ではなく、役職が明記されている人のみを抽出してください
        - 同じ人物が複数の役職を持つ場合は、両方のマッピングを作成してください

        # 出席者セクションの判定
        - 「出席議員」「出席説明員」「出席者」などのセクションが見つかった場合: attendee_section_found = true
        - 出席者情報が見つからない場合: attendee_section_found = false

        # 信頼度の基準
        - 0.9以上: 明確な役職-人名の対応が複数見つかった
        - 0.7-0.9: 役職-人名の対応が見つかったが、一部不明確
        - 0.5-0.7: 出席者情報は見つかったが、役職の対応が不明確
        - 0.5未満: 出席者情報がほとんど見つからない

        # 出力形式
        出席者セクションが見つかった場合:
        {
          "mappings": [
            {"role": "議長", "name": "伊藤条一", "member_number": "100番"},
            {"role": "副議長", "name": "梶谷大志", "member_number": "82番"},
            {"role": "知事", "name": "鈴木直道", "member_number": null}
          ],
          "attendee_section_found": true,
          "confidence": 0.95
        }

        出席者セクションが見つからない場合:
        {
          "mappings": [],
          "attendee_section_found": false,
          "confidence": 0.0
        }

        {{ ctx.output_format }}
    "#
}
