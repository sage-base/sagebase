// Proposal Parliamentary Group Judge Extraction for Sagebase
// 議案への会派単位の賛否情報をLLMで抽出するためのBAML定義

// ========================================
// Enum Definitions
// ========================================

// 賛否タイプ
enum JudgmentType {
    FOR       @description("賛成")
    AGAINST   @description("反対")
    ABSTAIN   @description("棄権")
    ABSENT    @description("欠席")
}

// ========================================
// Class Definitions
// ========================================

// 会派単位の賛否情報
class ParliamentaryGroupJudgeExtraction {
    group_name string @description("会派名（抽出された生の文字列）")
    judgment JudgmentType @description("賛否")
    member_count int? @description("人数（判明している場合）")
    note string? @description("備考（特記事項がある場合）")
}

// ========================================
// Function Definitions
// ========================================

// 議会ページのHTMLから会派単位の賛否情報を抽出
function ExtractParliamentaryGroupJudges(
    html_text: string
) -> ParliamentaryGroupJudgeExtraction[] {
    client Gemini2Flash
    prompt #"
        以下の議会ページのHTMLテキストから、会派（議員団）単位の賛否情報を抽出してください。

        # 入力テキスト
        {{ html_text }}

        # 抽出対象
        各会派について以下の情報を抽出:
        1. 会派名（必須）: 議員団・会派の正式名称
        2. 賛否（必須）: FOR(賛成) / AGAINST(反対) / ABSTAIN(棄権) / ABSENT(欠席)
        3. 人数（任意）: その会派の賛否に参加した人数（記載がある場合のみ）
        4. 備考（任意）: 自由投票、一部反対など特記事項

        # 賛否の判定基準
        - 「賛成」「可決に賛成」「原案賛成」→ FOR
        - 「反対」「否決」「原案反対」→ AGAINST
        - 「棄権」→ ABSTAIN
        - 「欠席」「退席」→ ABSENT
        - 「賛成多数」「全会一致」などの場合は、個別の会派情報があればそちらを抽出

        # 注意事項
        - 会派名は元のページの表記を維持してください
        - 同じ会派が複数の議案に対して異なる賛否を示している場合は、それぞれ別のレコードとして抽出してください
        - 人数が明記されていない場合は null としてください
        - 個人名ではなく会派・議員団単位の賛否のみを抽出してください
        - 賛否情報が見つからない場合は空のリストを返してください

        {{ ctx.output_format }}
    "#
}
