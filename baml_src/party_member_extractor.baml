// Party Member Extraction for Sagebase
// 政党メンバー抽出用のBAML定義

// 抽出された政党メンバー情報の型定義
class ExtractedPartyMember {
    name string @description("議員の氏名（姓名、敬称なし）")
    position string? @description("役職（衆議院議員、参議院議員、市議会議員、区議会議員、県議会議員など）")
    electoral_district string? @description("選挙区（例：東京1区、比例北海道、渋谷区、盛岡市など）")
    prefecture string? @description("都道府県（例：東京都、北海道）")
    profile_url string? @description("プロフィールページのURL（相対URLまたは絶対URL）")
    party_position string? @description("党内役職（代表、幹事長など）")
}

// 政党メンバー抽出関数
function ExtractPartyMembers(
    content: string,
    party_name: string,
    base_url: string
) -> ExtractedPartyMember[] {
    client Gemini2Flash
    prompt #"
        以下のコンテンツから{{ party_name }}の議員メンバー情報を抽出してください。

        重要事項:
        - 議員名は姓名を正確に抽出してください（姓と名の間にスペースは不要）
        - 敬称（議員、氏、さん、様、先生など）は除外してください
        - プロフィールURLは以下のルールで抽出してください：
          * HTMLの<a>タグのhref属性から取得してください
          * 「プロフィール」「詳細」などのテキストそのものをURLにしないでください
          * 相対URLの場合は、基準URL {{ base_url }} と結合した絶対URLにしてください
          * リンクが見つからない場合はnullを設定してください
        - データが不明な場合はnullを設定してください
        - 議員ではない人物（事務局スタッフなど）は除外してください

        コンテンツ:
        {{ content }}

        以下のJSON形式で出力してください（スキーマのフィールド名を正確に使用）：
        - name: 議員の氏名（姓名、敬称なし、必須）
        - position: 役職（衆議院議員、参議院議員、市議会議員など）
        - electoral_district: 選挙区（東京1区、比例北海道、渋谷区など）
        - prefecture: 都道府県（東京都、北海道など）
        - profile_url: プロフィールページのURL（<a>タグのhrefから抽出、絶対URL形式）
        - party_position: 党内役職（代表、幹事長など）

        ※不明な項目はnullとしてください
    "#
}
