"""議員団関連のCLIコマンド"""

import click

from src.infrastructure.di.container import get_container, init_container


@click.command("list-parliamentary-groups")
@click.option(
    "--conference-id",
    type=int,
    help="特定の会議体の議員団のみ表示",
)
@click.option(
    "--with-members",
    is_flag=True,
    help="現在のメンバー数も表示",
)
@click.option(
    "--active-only/--all",
    default=True,
    help="活動中の議員団のみ表示するか",
)
def list_parliamentary_groups(
    conference_id: int | None,
    with_members: bool,
    active_only: bool,
):
    """議員団の一覧を表示"""
    # Initialize and get dependencies from DI container
    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    session = container.database.session()

    # Import repository implementations
    from src.infrastructure.persistence.parliamentary_group_repository_impl import (
        ParliamentaryGroupMembershipRepositoryImpl,
        ParliamentaryGroupRepositoryImpl,
    )
    from src.infrastructure.persistence.repository_adapter import RepositoryAdapter

    group_repo = RepositoryAdapter(ParliamentaryGroupRepositoryImpl, session)
    membership_repo = RepositoryAdapter(
        ParliamentaryGroupMembershipRepositoryImpl, session
    )

    # 議員団を取得（会議体・行政機関情報も含む）
    groups = group_repo.get_all_with_details(
        conference_id=conference_id, active_only=active_only
    )

    if not groups:
        click.echo(click.style("議員団が見つかりません", fg="yellow"))
        return

    # 表形式で表示
    click.echo("\n議員団一覧")
    click.echo("-" * 80)

    # ヘッダー
    headers = ["ID", "議員団名", "会議体", "行政機関", "URL", "状態"]
    if with_members:
        headers.append("メンバー数")

    # ヘッダー行を表示
    header_line = " | ".join(h.ljust(15) if h != "ID" else h.ljust(6) for h in headers)
    click.echo(header_line)
    click.echo("-" * len(header_line))

    # 各議員団の情報を表示
    for group in groups:
        row_data: list[str] = [
            str(group["id"]).ljust(6),
            group["name"][:15].ljust(15),
            group.get("conference_name", "N/A")[:15].ljust(15),
            group.get("governing_body_name", "N/A")[:15].ljust(15),
            (group.get("url", "未設定") if group.get("url") else "未設定")[:15].ljust(
                15
            ),
            ("活動中" if group.get("is_active", True) else "非活動").ljust(15),
        ]

        if with_members:
            # 現在のメンバー数を取得
            members = membership_repo.get_current_members(group["id"])
            row_data.append(str(len(members)).ljust(15))

        click.echo(" | ".join(row_data))

    click.echo(f"\n総数: {len(groups)} 議員団")


def get_parliamentary_group_commands():
    """Get all parliamentary group related commands"""
    return [
        list_parliamentary_groups,
    ]
