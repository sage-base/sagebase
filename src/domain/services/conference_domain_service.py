"""Conference domain service for handling conference-related business logic."""

from datetime import date, datetime

from src.domain.entities.conference import Conference


class ConferenceDomainService:
    """Domain service for conference-related business logic."""

    def extract_member_role(self, text: str) -> str | None:
        """Extract member role from text."""
        # Common roles in Japanese councils
        role_mappings = {
            "議長": "議長",
            "副議長": "副議長",
            "委員長": "委員長",
            "副委員長": "副委員長",
            "議運委員長": "議運委員長",
            "監査委員": "監査委員",
            "代表": "代表",
            "幹事長": "幹事長",
            "団長": "団長",
        }

        for pattern, role in role_mappings.items():
            if pattern in text:
                return role

        return None

    def normalize_party_name(self, party_name: str) -> str:
        """Normalize party name for matching."""
        if not party_name:
            return ""

        # Remove common suffixes and normalize
        normalized = party_name.strip()

        # Remove party/group suffixes
        suffixes = ["の会", "会派", "議員団", "クラブ", "市民の会"]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()

        return normalized

    def calculate_affiliation_overlap(
        self,
        start_date1: date,
        end_date1: date | None,
        start_date2: date,
        end_date2: date | None,
    ) -> bool:
        """Check if two affiliation periods overlap."""
        # If either period is ongoing (end_date is None), check if start dates conflict
        if end_date1 is None and end_date2 is None:
            return True  # Both ongoing

        if end_date1 is None:
            return start_date1 <= (end_date2 or datetime.now().date())

        if end_date2 is None:
            return start_date2 <= (end_date1 or datetime.now().date())

        # Both have end dates
        return start_date1 <= end_date2 and start_date2 <= end_date1

    def validate_affiliation_dates(
        self, start_date: date, end_date: date | None
    ) -> list[str]:
        """Validate affiliation date range."""
        issues: list[str] = []

        # Start date should not be in the future
        if start_date > datetime.now().date():
            issues.append("Start date cannot be in the future")

        # End date should be after start date
        if end_date and end_date < start_date:
            issues.append("End date must be after start date")

        # Reasonable date range (not before 1900)
        if start_date.year < 1900:
            issues.append("Start date seems too old")

        return issues

    def group_conferences_by_governing_body(
        self, conferences: list[Conference]
    ) -> dict[int, list[Conference]]:
        """Group conferences by their governing body."""
        grouped: dict[int, list[Conference]] = {}

        for conference in conferences:
            body_id = conference.governing_body_id
            if body_id not in grouped:
                grouped[body_id] = []
            grouped[body_id].append(conference)

        return grouped

    def infer_conference_type(self, conference_name: str) -> str:
        """Infer conference type from its name."""
        # Check for committee types
        if "委員会" in conference_name:
            if "常任" in conference_name:
                return "常任委員会"
            elif "特別" in conference_name:
                return "特別委員会"
            elif "議会運営" in conference_name:
                return "議会運営委員会"
            else:
                return "委員会"

        # Check for full council
        if "議会" in conference_name and "全" in conference_name:
            return "議会全体"

        # Check for plenary session
        if "本会議" in conference_name:
            return "本会議"

        # Default
        return "その他"

    def calculate_member_confidence_score(
        self,
        extracted_name: str,
        politician_name: str,
        party_match: bool,
        role_match: bool,
    ) -> float:
        """Calculate confidence score for member matching."""
        # Base score from name similarity
        name_score = self._calculate_name_similarity(extracted_name, politician_name)

        # Boost for party match
        if party_match:
            name_score += 0.2

        # Boost for role match
        if role_match:
            name_score += 0.1

        # Cap at 1.0
        return min(name_score, 1.0)

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        # Normalize names
        norm1 = name1.strip().replace(" ", "").replace("　", "")
        norm2 = name2.strip().replace(" ", "").replace("　", "")

        if norm1 == norm2:
            return 1.0

        # Check if one contains the other
        if norm1 in norm2 or norm2 in norm1:
            return 0.9

        # Character-based similarity
        chars1 = set(norm1)
        chars2 = set(norm2)

        if not chars1 or not chars2:
            return 0.0

        intersection = chars1 & chars2
        union = chars1 | chars2

        return len(intersection) / len(union)
