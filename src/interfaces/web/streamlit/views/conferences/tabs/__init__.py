"""Tabs for conferences management.

会議体管理の各タブモジュールを提供します。
"""

from .edit_delete_tab import render_edit_delete_form
from .list_tab import render_conferences_list
from .new_tab import render_new_conference_form
from .seed_generator_tab import render_seed_generator


__all__ = [
    "render_conferences_list",
    "render_edit_delete_form",
    "render_new_conference_form",
    "render_seed_generator",
]
