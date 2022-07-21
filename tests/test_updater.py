import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import updater
from pytest_mock import MockerFixture
from updater import POETRY_CONFIG_FILE_NAME, run_updater


@dataclass
class Project:
    """
    Poetry TOML file before/after contents.
    """

    before: str
    after: str
    path: str = ""


def _run_updater(projects: list[Project], *, add_tool_poetry: bool = True, tmp_dir: str = None) -> None:
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

                    {project.before}
                    """
            project.after = f"""
                    [tool.poetry]
                    name = "{project_name}"
                    version = "1.0.0"
                    description = ""
                    authors = []

                    {project.after}
                    """

        # Normalize the lines.
        project.before = "\n".join(line.strip() for line in project.before.split("\n"))
        project.after = "\n".join(line.strip() for line in project.after.split("\n"))

    def run_in_tmp_directory():
        # Create the files
        for project in projects:
            file_path = Path(tmp_dir) / project.path / POETRY_CONFIG_FILE_NAME
            os.mkdir(file_path.parent.resolve())
            open(file_path, "w").write(project.before)

        # Run the updater.
        run_updater([tmp_dir])

        # Compare the files.
        for project in projects:
            file_path = Path(tmp_dir) / project.path / POETRY_CONFIG_FILE_NAME
            assert project.after == open(file_path).read()

    if tmp_dir:
        run_in_tmp_directory()
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_in_tmp_directory()


def test_poetry_deps():
    """A package under `dependencies` is out of date"""
    _run_updater(
        [
            Project(
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                shpyx = "0.0.13"
                """,
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                shpyx = "0.0.14"
                """,
            )
        ]
    )


def test_poetry_dev_deps():
    """A package under `dev-dependencies` is out of date"""
    _run_updater(
        [
            Project(
                """
                [tool.poetry.dependencies]
                python = "^3.10"

                [tool.poetry.dev-dependencies]
                shpyx = "0.0.13"
                """,
                """
                [tool.poetry.dependencies]
                python = "^3.10"

                [tool.poetry.dev-dependencies]
                shpyx = "0.0.14"
                """,
            )
        ]
    )


def test_multiline_deps():
    """A package with a multi-line configuration is out of date"""
    _run_updater(
        [
            Project(
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                sqlalchemy = { extras = [
                  "postgresql",
                  "postgresql_asyncpg"
                ], version = "1.4.36" }
                """,
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                sqlalchemy = { extras = [
                  "postgresql",
                  "postgresql_asyncpg"
                ], version = "1.4.39" }
                """,
            )
        ]
    )


def test_no_changes():
    """Everything is up to date"""
    _run_updater(
        [
            Project(
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                shpyx = "0.0.14"
                """,
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                shpyx = "0.0.14"
                """,
            )
        ]
    )


def test_casing():
    """Verify that lower/upper case in package names is preserved"""
    _run_updater(
        [
            Project(
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                sHpYx = "0.0.13"
                """,
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                sHpYx = "0.0.14"
                """,
            )
        ]
    )


def test_path_dependency_run_order(mocker: MockerFixture):
    """Verify that path dependencies are updated first"""
    # Track calls to "shpyx.run".
    shpyx_run_spy = mocker.spy(updater.shpyx, "run")

    tmp_dir = tempfile.TemporaryDirectory()

    # Make sure the results of `os.walk` are not in the correct update order.
    def _os_walk(path: str, *args, **kwargs):
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
                python = "^3.10"
                inner_1 = { path = "../inner_1", develop = true }
                inner_2 = { path = "../inner_2", develop = false }
                """,
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                inner_1 = { path = "../inner_1", develop = true }
                inner_2 = { path = "../inner_2", develop = false }
                """,
                "outer",
            ),
            Project(
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                inner_2 = { path = "../inner_2", develop = false }
                """,
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                inner_2 = { path = "../inner_2", develop = false }
                """,
                "inner_1",
            ),
            Project(
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                shpyx = "0.0.13"
                """,
                """
                [tool.poetry.dependencies]
                python = "^3.10"
                shpyx = "0.0.14"
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
        ("poetry update --lock", "inner_2"),
        ("poetry show -o --no-ansi", "inner_2"),
        ("poetry update --lock", "inner_2"),
        ("poetry update --lock", "inner_1"),
        ("poetry show -o --no-ansi", "inner_1"),
        ("poetry update --lock", "outer"),
        ("poetry show -o --no-ansi", "outer"),
    ]
