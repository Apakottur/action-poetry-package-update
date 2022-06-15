import tempfile
from pathlib import Path

from updater import POETRY_CONFIG_FILE_NAME, run_updater


def _run_updater(before: str, after: str) -> None:
    """
    Run the update and verify the result.

    Args:
        before: Contents of the Poetry config file before the update.
        after: Contents of the Poetry config file after the update.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create the file.
        file_path = Path(tmp_dir) / POETRY_CONFIG_FILE_NAME
        open(file_path, "w").write(before)

        # Run the updater.
        run_updater([tmp_dir])

        # Compare the files.
        assert after == open(file_path).read()


def test_poetry_deps():
    """A package under `dependencies` is out of date"""
    _run_updater(
        """
        [tool.poetry]
        name = "test"
        version = "1.0.0"
        description = ""
        authors = []

        [tool.poetry.dependencies]
        python = "3.10"
        shpyx = "0.0.13"
        """,
        """
        [tool.poetry]
        name = "test"
        version = "1.0.0"
        description = ""
        authors = []

        [tool.poetry.dependencies]
        python = "3.10"
        shpyx = "0.0.14"
        """,
    )


def test_poetry_dev_deps():
    """A package under `dev-dependencies` is out of date"""
    _run_updater(
        """
        [tool.poetry]
        name = "test"
        version = "1.0.0"
        description = ""
        authors = []

        [tool.poetry.dependencies]
        python = "3.10"

        [tool.poetry.dev-dependencies]
        shpyx = "0.0.13"
        """,
        """
        [tool.poetry]
        name = "test"
        version = "1.0.0"
        description = ""
        authors = []

        [tool.poetry.dependencies]
        python = "3.10"

        [tool.poetry.dev-dependencies]
        shpyx = "0.0.14"
        """,
    )


def test_multiline_deps():
    """A package with a multi-line configuration is out of date"""
    _run_updater(
        """
        [tool.poetry]
        name = "test"
        version = "1.0.0"
        description = ""
        authors = []

        [tool.poetry.dependencies]
        python = "3.10"
        sqlalchemy = { extras = [
          "postgresql",
          "postgresql_asyncpg"
        ], version = "1.4.36" }
        """,
        """
        [tool.poetry]
        name = "test"
        version = "1.0.0"
        description = ""
        authors = []

        [tool.poetry.dependencies]
        python = "3.10"
        sqlalchemy = { extras = [
          "postgresql",
          "postgresql_asyncpg"
        ], version = "1.4.37" }
        """,
    )


def test_no_changes():
    """Everything is up to date"""
    _run_updater(
        """
        [tool.poetry]
        name = "test"
        version = "1.0.0"
        description = ""
        authors = []

        [tool.poetry.dependencies]
        python = "3.10"
        shpyx = "0.0.14"
        """,
        """
        [tool.poetry]
        name = "test"
        version = "1.0.0"
        description = ""
        authors = []

        [tool.poetry.dependencies]
        python = "3.10"
        shpyx = "0.0.14"
        """,
    )
