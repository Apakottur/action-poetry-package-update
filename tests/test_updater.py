import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pytest_mock import MockerFixture

import src.updater
from src.updater import POETRY_CONFIG_FILE_NAME, run_updater

SHPYX_OLD_VERSION = '"0.0.13"'
SHPYX_NEW_VERSION = '"0.0.33"'

SQLA_OLD_VERSION = '"1.4.36"'
SQLA_NEW_VERSION = '"2.0.40"'

PIL_OLD_VERSION = '"10.4.0"'
PIL_NEW_VERSION = '"11.1.0"'


@dataclass
class Project:
    """
    Poetry project configuration.
    """

    # The contents of the TOML file before the update.
    before: str

    # The contents of the TOML file after the update.
    after: str

    # The relative path to the project file.
    path: str = ""


def _run_updater(
    projects: list[Project],
    *,
    add_tool_poetry: bool = True,
    tmp_dir: str | None = None,
) -> None:
    """
    Run the updater and verify the result.

    Args:
        projects: Poetry project details
        add_tool_poetry: Whether to add a "tool.poetry" clause to the files.
        tmp_dir: Temporary directory to use. If None, one is created.
    """
    # Prepare file details.
    for project in projects:
        project_name = Path(project.path).name

        # Add "tool.poetry" section if needed.
        if add_tool_poetry:
            project.before = f"""
                    [tool.poetry]
                    name = "{project_name}"
                    version = "1.0.0"
                    description = ""
                    authors = []
                    package-mode = false

                    {project.before}
                    """
            project.after = f"""
                    [tool.poetry]
                    name = "{project_name}"
                    version = "1.0.0"
                    description = ""
                    authors = []
                    package-mode = false

                    {project.after}
                    """

        # Normalize the lines.
        project.before = "\n".join(line.strip() for line in project.before.split("\n"))
        project.after = "\n".join(line.strip() for line in project.after.split("\n"))

    def run_in_tmp_directory(_tmp_dir: str) -> None:
        # Create the files
        for p in projects:
            file_path = Path(_tmp_dir) / p.path / POETRY_CONFIG_FILE_NAME
            Path.mkdir(file_path.parent, exist_ok=True)
            Path(file_path).write_text(p.before)

        # Run the updater.
        run_updater([_tmp_dir])

        # Compare the files.
        for p in projects:
            file_path = Path(_tmp_dir) / p.path / POETRY_CONFIG_FILE_NAME
            assert p.after == Path(file_path).read_text()

    # Create a temporary directory or use an existing run and then run the updater.
    if tmp_dir:
        run_in_tmp_directory(tmp_dir)
    else:
        with tempfile.TemporaryDirectory() as _tmp_dir:
            run_in_tmp_directory(_tmp_dir)


def test_poetry_deps() -> None:
    """A package under `dependencies` is out of date"""
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_OLD_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_NEW_VERSION}
                """,
            )
        ]
    )


def test_poetry_dev_deps() -> None:
    """A package under `dev-dependencies` is out of date"""
    # Old syntax.
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"

                [tool.poetry.dev-dependencies]
                shpyx = {SHPYX_OLD_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"

                [tool.poetry.dev-dependencies]
                shpyx = {SHPYX_NEW_VERSION}
                """,
            )
        ]
    )

    # New syntax.
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"

                [tool.poetry.group.dev.dependencies]
                shpyx = {SHPYX_OLD_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"

                [tool.poetry.group.dev.dependencies]
                shpyx = {SHPYX_NEW_VERSION}
                """,
            )
        ]
    )


def test_multiline_deps() -> None:
    """A package with a multi-line configuration is out of date"""
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                sqlalchemy = {{ extras = [
                  "postgresql",
                  "postgresql_asyncpg"
                ], version = {SQLA_OLD_VERSION} }}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                sqlalchemy = {{ extras = [
                  "postgresql",
                  "postgresql_asyncpg"
                ], version = {SQLA_NEW_VERSION} }}
                """,
            )
        ]
    )


def test_no_changes() -> None:
    """Everything is up to date"""
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_NEW_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_NEW_VERSION}
                """,
            )
        ]
    )


def test_casing() -> None:
    """Verify that lower/upper case in package names is preserved"""
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_OLD_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_NEW_VERSION}
                """,
            )
        ]
    )


def test_path_dependency_run_order(mocker: MockerFixture) -> None:
    """Verify that the update order is correct when using path dependencies"""
    # Track calls to "shpyx.run".
    shpyx_run_spy = mocker.spy(src.updater.shpyx, "run")

    tmp_dir = tempfile.TemporaryDirectory()

    # Make sure the results of `os.walk` are NOT in the correct update order.
    def _os_walk(path: str, *args: Any, **kwargs: Any) -> list[tuple[str, list[str], list[str]]]:
        assert (path, args, kwargs) == (tmp_dir.name, (), {})
        return [
            (tmp_dir, ["outer", "inner_1", "inner_2"], []),
            (f"{tmp_dir.name}/outer", ["outer"], [POETRY_CONFIG_FILE_NAME]),
            (f"{tmp_dir.name}/inner_1", ["inner_1"], [POETRY_CONFIG_FILE_NAME]),
            (f"{tmp_dir.name}/inner_2", ["inner_2"], [POETRY_CONFIG_FILE_NAME]),
        ]

    mocker.patch("updater.os.walk", _os_walk)

    _run_updater(
        [
            Project(
                """
                [tool.poetry.dependencies]
                python = "~3.12"
                inner_1 = { path = "../inner_1", develop = true }
                inner_2 = { path = "../inner_2", develop = false }
                """,
                """
                [tool.poetry.dependencies]
                python = "~3.12"
                inner_1 = { path = "../inner_1", develop = true }
                inner_2 = { path = "../inner_2", develop = false }
                """,
                "outer",
            ),
            Project(
                """
                [tool.poetry.dependencies]
                python = "~3.12"
                inner_2 = { path = "../inner_2", develop = false }
                """,
                """
                [tool.poetry.dependencies]
                python = "~3.12"
                inner_2 = { path = "../inner_2", develop = false }
                """,
                "inner_1",
            ),
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_OLD_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_NEW_VERSION}
                """,
                "inner_2",
            ),
        ],
        tmp_dir=tmp_dir.name,
    )

    tmp_dir.cleanup()

    # Verify that the updates were called in the correct order.
    cmd_runs = [(mock_call.args[0], Path(mock_call.kwargs["exec_dir"]).name) for mock_call in shpyx_run_spy.mock_calls]
    assert cmd_runs == [
        ("poetry lock", "inner_2"),
        ("poetry lock", "inner_1"),
        ("poetry lock", "outer"),
        ("poetry show -o --no-ansi", "inner_2"),
        ("poetry update --lock", "inner_2"),
        ("poetry show -o --no-ansi", "inner_1"),
        ("poetry update --lock", "inner_1"),
        ("poetry show -o --no-ansi", "outer"),
        ("poetry update --lock", "outer"),
    ]


def test_path_dependency_duplicates_dependency() -> None:
    """Verify that the update succeeds when both the main project and the path dependency have the same dependency"""
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                inner = {{ path = "../inner", develop = true }}
                shpyx = {SHPYX_OLD_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                inner = {{ path = "../inner", develop = true }}
                shpyx = {SHPYX_NEW_VERSION}
                """,
                "outer",
            ),
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_OLD_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_NEW_VERSION}
                """,
                "inner",
            ),
        ],
    )


def test_locked_version() -> None:
    """Verify that packages with a '==' are ignored for updates"""
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_OLD_VERSION}
                sqlalchemy = "==1.4.36" # Locked for some reason.
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_NEW_VERSION}
                sqlalchemy = "==1.4.36" # Locked for some reason.
                """,
            )
        ]
    )


def test_custom_groups() -> None:
    """Verify that packages under custom groups are updates"""
    _run_updater(
        [
            Project(
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_OLD_VERSION}

                [tool.poetry.group.first_group]
                optional = true

                [tool.poetry.group.first_group.dependencies]
                sqlalchemy = {SQLA_OLD_VERSION}

                [tool.poetry.group.second_group.dependencies]
                pillow = {PIL_OLD_VERSION}
                """,
                f"""
                [tool.poetry.dependencies]
                python = "~3.12"
                shpyx = {SHPYX_NEW_VERSION}

                [tool.poetry.group.first_group]
                optional = true

                [tool.poetry.group.first_group.dependencies]
                sqlalchemy = {SQLA_NEW_VERSION}

                [tool.poetry.group.second_group.dependencies]
                pillow = {PIL_NEW_VERSION}
                """,
            )
        ]
    )
