"""データ整合性バリデーションのCLIコマンド."""

import click

from src.interfaces.cli.base import (
    BaseCommand,
    ensure_container,
    with_async_execution,
    with_error_handling,
)


@click.command("validate-data-integrity")
@click.option(
    "--verbose",
    is_flag=True,
    help="問題の詳細を表示する",
)
@click.option(
    "--check",
    type=click.Choice(
        [
            "party-membership-overlap",
            "membership-period",
            "group-overlap",
            "orphaned-fk",
        ]
    ),
    help="特定のチェックのみ実行する",
)
@with_error_handling
@with_async_execution
async def validate_data_integrity(verbose: bool, check: str | None) -> None:
    """データ整合性を検証する.

    以下のチェックを実行し、結果をサマリ表示する:
    - 同一政治家の政党所属期間重複チェック
    - 会派存続期間とメンバーシップ期間の整合性チェック
    - 同一会派名の時代重複チェック
    - 孤立FK参照チェック
    """
    from src.application.usecases.validate_data_integrity_usecase import (
        ValidateDataIntegrityUseCase,
    )

    container = ensure_container()
    session = container.database.async_session()
    usecase = ValidateDataIntegrityUseCase(session)
    report = await usecase.execute()

    # 指定されたチェックのみフィルタ
    check_name_map = {
        "party-membership-overlap": "政党所属期間の重複チェック",
        "membership-period": "メンバーシップ期間の整合性チェック",
        "group-overlap": "会派の時代重複チェック",
        "orphaned-fk": "孤立FK参照チェック",
    }

    if check:
        target_name = check_name_map[check]
        report.checks = [c for c in report.checks if c.name == target_name]

    # 結果表示
    click.echo("\n=== データ整合性チェック結果 ===\n")

    for result in report.checks:
        if result.passed:
            status = click.style("PASS", fg="green")
        else:
            status = click.style("FAIL", fg="red")
        click.echo(f"  [{status}] {result.name}: {result.summary}")

        if verbose and not result.passed:
            for issue in result.issues:
                click.echo(f"        - {issue.description}")

    click.echo("")

    if report.all_passed:
        BaseCommand.success(f"全{len(report.checks)}チェック通過")
    else:
        BaseCommand.warning(f"合計 {report.total_issues} 件の問題を検出")
        raise SystemExit(1)


def get_data_validation_commands() -> list[click.Command]:
    """データバリデーション関連のコマンドを返す."""
    return [validate_data_integrity]
