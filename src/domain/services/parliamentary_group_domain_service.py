"""Parliamentary group domain service."""

from datetime import date, datetime
from typing import Any

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.services.name_similarity_calculator import NameSimilarityCalculator


class ParliamentaryGroupDomainService:
    """Domain service for parliamentary group business logic."""

    def normalize_group_name(self, name: str) -> str:
        """Normalize parliamentary group name for matching."""
        if not name:
            return ""

        # Remove common suffixes
        normalized = name.strip()
        suffixes = ["議員団", "会派", "の会", "クラブ"]

        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()

        return normalized

    def extract_role_from_text(self, text: str) -> str | None:
        """Extract parliamentary group role from text."""
        # Common roles in parliamentary groups
        role_patterns = {
            "団長": "団長",
            "幹事長": "幹事長",
            "政調会長": "政調会長",
            "政策委員長": "政策委員長",
            "代表": "代表",
            "副団長": "副団長",
            "副幹事長": "副幹事長",
            "会計": "会計",
            "監査": "監査",
        }

        for pattern, role in role_patterns.items():
            if pattern in text:
                return role

        return None

    def validate_membership_dates(
        self,
        start_date: date,
        end_date: date | None,
        existing_memberships: list[tuple[date, date | None]],
    ) -> list[str]:
        """Validate membership dates against existing memberships."""
        issues: list[str] = []

        # Basic date validation
        if end_date and end_date < start_date:
            issues.append("End date must be after start date")

        # Check for overlapping memberships
        for existing_start, existing_end in existing_memberships:
            if self._dates_overlap(start_date, end_date, existing_start, existing_end):
                overlap_msg = (
                    f"Membership overlaps with existing period: "
                    f"{existing_start} to {existing_end or 'present'}"
                )
                issues.append(overlap_msg)

        return issues

    def _dates_overlap(
        self,
        start1: date,
        end1: date | None,
        start2: date,
        end2: date | None,
    ) -> bool:
        """Check if two date ranges overlap."""
        # If either is ongoing, check if starts conflict
        if end1 is None and end2 is None:
            return True

        if end1 is None:
            return start1 <= (end2 or datetime.now().date())

        if end2 is None:
            return start2 <= (end1 or datetime.now().date())

        return start1 <= end2 and start2 <= end1

    def merge_group_memberships(
        self,
        memberships: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge adjacent memberships with same group and role."""
        if not memberships:
            return []

        # Sort by start date
        sorted_memberships = sorted(memberships, key=lambda m: m["start_date"])

        merged: list[dict[str, Any]] = []
        current = sorted_memberships[0].copy()

        for membership in sorted_memberships[1:]:
            # Check if can merge with current
            if (
                membership["parliamentary_group_id"]
                == current["parliamentary_group_id"]
                and membership["role"] == current["role"]
                and self._can_merge_periods(
                    current["end_date"], membership["start_date"]
                )
            ):
                # Extend current membership
                current["end_date"] = membership["end_date"]
            else:
                # Save current and start new
                merged.append(current)
                current = membership.copy()

        # Add last membership
        merged.append(current)

        return merged

    def _can_merge_periods(self, end_date: date | None, start_date: date) -> bool:
        """Check if two periods can be merged (adjacent or overlapping)."""
        if end_date is None:
            return True  # Current period is ongoing

        # Allow merge if periods are within 1 day
        days_diff = (start_date - end_date).days
        return days_diff <= 1

    def calculate_group_strength(
        self,
        group: ParliamentaryGroup,
        member_count: int,
        total_members: int,
    ) -> dict[str, Any]:
        """Calculate parliamentary group strength metrics."""
        if total_members == 0:
            percentage = 0.0
        else:
            percentage = (member_count / total_members) * 100

        # Determine if it's a majority, minority, etc.
        status = "その他"
        if percentage > 50:
            status = "過半数"
        elif percentage >= 33.3:
            status = "大会派"
        elif percentage >= 20:
            status = "中会派"
        elif percentage >= 10:
            status = "小会派"
        else:
            status = "少数会派"

        return {
            "group_id": group.id,
            "group_name": group.name,
            "member_count": member_count,
            "percentage": round(percentage, 2),
            "status": status,
            "is_active": group.is_active,
        }

    def find_similar_groups(
        self,
        name: str,
        groups: list[ParliamentaryGroup],
        threshold: float = 0.7,
    ) -> list[ParliamentaryGroup]:
        """Find parliamentary groups with similar names."""
        normalized_target = self.normalize_group_name(name)
        similar: list[ParliamentaryGroup] = []

        for group in groups:
            normalized_name = self.normalize_group_name(group.name)
            similarity = self._calculate_similarity(normalized_target, normalized_name)

            if similarity >= threshold:
                similar.append(group)

        return similar

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        return NameSimilarityCalculator.jaccard_with_containment(name1, name2)

    def group_politicians_by_parliamentary_group(
        self,
        memberships: list[dict[str, Any]],
    ) -> dict[int, list[dict[str, Any]]]:
        """Group current politicians by their parliamentary groups."""
        current_date = datetime.now().date()
        grouped: dict[int, list[dict[str, Any]]] = {}

        for membership in memberships:
            # Check if membership is current
            if membership["start_date"] <= current_date:
                if (
                    membership["end_date"] is None
                    or membership["end_date"] >= current_date
                ):
                    group_id = membership["parliamentary_group_id"]
                    if group_id not in grouped:
                        grouped[group_id] = []
                    grouped[group_id].append(membership)

        return grouped
