"""会派賛否マッチングのDTO."""

from dataclasses import dataclass, field


@dataclass
class MatchProposalGroupJudgesInputDto:
    """会派賛否マッチング入力DTO."""

    governing_body_id: int
    dry_run: bool = False


@dataclass
class MatchProposalGroupJudgesOutputDto:
    """会派賛否マッチング出力DTO."""

    total_pending: int = 0
    matched: int = 0
    unmatched: int = 0
    judges_created: int = 0
    unmatched_names: list[str] = field(default_factory=list)
