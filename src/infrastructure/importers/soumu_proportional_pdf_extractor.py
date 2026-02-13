"""総務省比例代表PDFファイルからGemini APIで構造化データを抽出する.

第45-47, 49-50回の比例代表当選者データをPDFから抽出する。
Gemini 2.0 Flash以降のPDFネイティブ入力機能を使用。
"""

import base64
import json
import logging
import os

from datetime import date
from pathlib import Path

from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
    ProportionalElectionInfo,
)
from src.infrastructure.importers._constants import PROPORTIONAL_BLOCKS


logger = logging.getLogger(__name__)

# Gemini に送るプロンプト
EXTRACTION_PROMPT = """\
以下のPDFは日本の衆議院議員総選挙の比例代表「党派別当選人数」です。

PDFから以下の情報を抽出しJSONで出力してください。

## 抽出ルール

1. 各比例ブロック（北海道、東北、北関東、南関東、東京、\
北陸信越、東海、近畿、中国、四国、九州）ごとに抽出。
2. 当選者のみを抽出（名簿登載者全員ではなく当選人のみ）。
3. 候補者名は姓と名の間に半角スペースを入れる。
4. 小選挙区結果は "当"/"落"/""（比例単独）の3値。
5. 惜敗率は小数点以下3桁。重複立候補でなければnull。

## 出力JSON

{"election_date":"YYYY-MM-DD","blocks":[{"block_name":"北海道",\
"parties":[{"party_name":"自由民主党","votes":641127,\
"winners_count":3,"candidates":[{"name":"渡辺 孝一",\
"list_order":1,"smd_result":"落","loss_ratio":92.714}]}]}]}

JSONのみを出力してください。説明文は不要です。"""


def extract_from_pdf(
    pdf_path: Path,
    election_number: int,
    api_key: str | None = None,
) -> tuple[ProportionalElectionInfo | None, list[ProportionalCandidateRecord]]:
    """PDFファイルからGemini APIで比例代表データを抽出する.

    Args:
        pdf_path: PDFファイルのパス
        election_number: 選挙回次
        api_key: Google API Key（省略時は環境変数から取得）

    Returns:
        (選挙情報, 比例代表候補者レコードのリスト)
    """
    resolved_key = api_key or os.getenv("GOOGLE_API_KEY")
    if not resolved_key:
        logger.error("GOOGLE_API_KEYが設定されていません")
        return None, []

    # PDFをbase64エンコード
    pdf_bytes = pdf_path.read_bytes()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    logger.info(
        "Gemini APIでPDF抽出開始: %s (%.1f MB)",
        pdf_path.name,
        len(pdf_bytes) / 1024 / 1024,
    )

    # LangChain経由でGemini APIを呼び出す
    try:
        from langchain_core.messages import HumanMessage
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.0,
            google_api_key=resolved_key,
        )

        message = HumanMessage(
            content=[
                {"type": "text", "text": EXTRACTION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:application/pdf;base64,{pdf_b64}"},
                },
            ]
        )

        response = model.invoke([message])
        response_text = response.content
        if not isinstance(response_text, str):
            response_text = str(response_text)

    except Exception:
        logger.exception("Gemini API呼び出しに失敗")
        return None, []

    # JSONをパース
    return _parse_gemini_response(response_text, election_number)


def _parse_gemini_response(
    response_text: str,
    election_number: int,
) -> tuple[ProportionalElectionInfo | None, list[ProportionalCandidateRecord]]:
    """Gemini APIの応答テキストからデータを抽出する.

    Args:
        response_text: Gemini APIの応答テキスト（JSON）
        election_number: 選挙回次

    Returns:
        (選挙情報, 比例代表候補者レコードのリスト)
    """
    # JSON部分を抽出（マークダウンコードブロック対応）
    json_text = response_text.strip()
    if json_text.startswith("```"):
        # ```json ... ``` の形式を処理
        lines = json_text.split("\n")
        start = 1  # 最初の```行をスキップ
        end = len(lines) - 1  # 最後の```行をスキップ
        if lines[-1].strip() == "```":
            end = len(lines) - 1
        json_text = "\n".join(lines[start:end])

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        logger.error("JSON解析失敗: %s...", json_text[:200])
        return None, []

    # 選挙日を取得
    election_info: ProportionalElectionInfo | None = None
    election_date_str = data.get("election_date", "")
    if election_date_str:
        try:
            election_info = ProportionalElectionInfo(
                election_number=election_number,
                election_date=date.fromisoformat(election_date_str),
            )
        except ValueError:
            logger.warning("選挙日のパースに失敗: %s", election_date_str)

    # 候補者データを変換
    all_candidates: list[ProportionalCandidateRecord] = []
    blocks = data.get("blocks", [])

    for block_data in blocks:
        block_name = block_data.get("block_name", "")
        if block_name not in PROPORTIONAL_BLOCKS:
            logger.warning("未知のブロック名: %s", block_name)
            continue

        parties = block_data.get("parties", [])
        for party_data in parties:
            party_name = party_data.get("party_name", "")
            winners_count = party_data.get("winners_count", 0)
            candidates_data = party_data.get("candidates", [])

            for idx, cand in enumerate(candidates_data):
                name = cand.get("name", "")
                if not name:
                    continue

                list_order = cand.get("list_order", idx + 1)
                smd_result = cand.get("smd_result", "")
                loss_ratio = cand.get("loss_ratio")

                # 当選判定: 当選者リスト内に含まれている = 当選
                is_elected = (idx + 1) <= winners_count

                candidate = ProportionalCandidateRecord(
                    name=name,
                    party_name=party_name,
                    block_name=block_name,
                    list_order=list_order,
                    smd_result=smd_result,
                    loss_ratio=loss_ratio,
                    is_elected=is_elected,
                )
                all_candidates.append(candidate)

    logger.info(
        "PDF抽出完了: %dブロック, %d候補者",
        len(blocks),
        len(all_candidates),
    )
    return election_info, all_candidates
