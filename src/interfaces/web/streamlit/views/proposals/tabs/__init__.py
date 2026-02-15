"""Tabs for proposals management.

議案管理の各タブモジュールを提供します。
"""

from .extracted_judges_tab import render_extracted_judges_tab
from .final_judges_tab import render_final_judges_tab
from .individual_vote_expansion_tab import render_individual_vote_expansion_tab
from .parliamentary_group_judges_tab import render_parliamentary_group_judges_tab
from .proposals_tab import render_proposals_tab
from .roll_call_override_tab import render_roll_call_override_tab


__all__ = [
    "render_extracted_judges_tab",
    "render_final_judges_tab",
    "render_individual_vote_expansion_tab",
    "render_parliamentary_group_judges_tab",
    "render_proposals_tab",
    "render_roll_call_override_tab",
]
