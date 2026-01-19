"""Tabs for parliamentary groups management.

議員団管理の各タブモジュールを提供します。
"""

from .edit_delete_tab import render_edit_delete_tab
from .list_tab import render_parliamentary_groups_list_tab
from .member_extraction_tab import render_member_extraction_tab
from .member_review_tab import render_member_review_tab
from .memberships_list_tab import render_memberships_list_tab
from .new_tab import render_new_parliamentary_group_tab


__all__ = [
    "render_edit_delete_tab",
    "render_member_extraction_tab",
    "render_member_review_tab",
    "render_memberships_list_tab",
    "render_new_parliamentary_group_tab",
    "render_parliamentary_groups_list_tab",
]
