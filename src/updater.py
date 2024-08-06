import functools
import os
from pathlib import Path

import shpyx
import tomlkit
import tomlkit.exceptions

"""Poetry configuration file name"""
POETRY_CONFIG_FILE_NAME = "pyproject.toml"

"""Sections in the Poetry configuration files where dependencies reside"""
SECTIONS = ("dependencies", "dev-dependencies", "group.dev.dependencies", "")


def _run_updater_in_path(path: str) -> None:
    """
    Run the updater in the specified path.
    """
    # Mapping from projects to their path dependencies.
    file_path_to_deps: dict[Path, list[Path]] = {}

    # First iteration - find all projects and create a mapping from projects to their path dependencies.
    for root, _dirs, files in os.walk(path):
        for name in files:
            # Skip non Poetry configuration files.
            if name != POETRY_CONFIG_FILE_NAME:
                continue

            # Get the contents of the configuration file.
            file_path = Path(root).joinpath(name)
            file_contents = Path(file_path).read_text()
            parsed_contents = tomlkit.parse(file_contents)

            # Get the poetry configuration, skipping if there is none.
            try:
                poetry_section = parsed_contents["tool"]["poetry"]
            except tomlkit.exceptions.NonExistentKey:
                continue

            # Build the mapping from projects to their path dependencies.
            file_path_to_deps[file_path.resolve()] = []
            for section in SECTIONS:
                try:
                    current_poetry_section = poetry_section
                    for part in section.split("."):
                        current_poetry_section = current_poetry_section[part]
                except tomlkit.exceptions.NonExistentKey:
                    continue

                for details in current_poetry_section.values():
                    if "path" in details:
                        file_path_to_deps[file_path.resolve()].append(
                            (Path(root) / details["path"] / name).resolve()
                        )

    # Order the projects based on interdependencies, where dependencies go first.
    def cmp(x: Path, y: Path) -> int:
        if x in file_path_to_deps[y]:
            # X is a dependency of Y, mark it as smaller, so it appears first in the list.
            return -1
        else:
            return 1

    file_paths_in_order = sorted(file_path_to_deps, key=functools.cmp_to_key(cmp))

    # Second iteration - run updates in order.
    for file_path in file_paths_in_order:
        # Get the contents of the configuration file.
        file_contents = Path(file_path).read_text()
        parsed_contents = tomlkit.parse(file_contents)
        poetry_section = parsed_contents["tool"]["poetry"]

        print(f"TOML contents of {file_path}: {parsed_contents}")

        # Update the lock file, creating it if needed.
        shpyx.run("poetry update --lock", exec_dir=file_path.parent)

        # Get all the outdated packages.
        results = shpyx.run("poetry show -o --no-ansi", exec_dir=file_path.parent)

        if not results.stdout:
            # Nothing to update.
            continue

        # Update the file contents, for each outdated package.
        for result in results.stdout.strip().split("\n"):
            # Remove the "(!)" decoration used to mark packages as non installed.
            formatted_result = result.replace(" (!) ", " ")

            # Get the package details.
            package_name, installed_version, new_version = formatted_result.split()[:3]

            # Update the package version in the file.
            for section in SECTIONS:
                try:
                    current_poetry_section = poetry_section
                    for part in section.split("."):
                        current_poetry_section = current_poetry_section[part]

                    original_package_name, package_details = next(
                        (name, details)
                        for name, details in current_poetry_section.items()
                        if name.lower() == package_name.lower()
                    )
                except (StopIteration, tomlkit.exceptions.NonExistentKey):
                    # Either the section is missing or the package is not in this section.
                    continue

                print(f"Updating {package_name}: {installed_version} -> {new_version}")

                # Replace the old version of the package with the new one.
                if isinstance(package_details, str):
                    current_poetry_section[original_package_name] = new_version
                else:
                    current_poetry_section[original_package_name]["version"] = (
                        new_version
                    )

        # Write the updated configuration file.
        Path(file_path).write_text(parsed_contents.as_string())

        # Finally, regenerate the lock file again, with the new package versions.
        shpyx.run("poetry update --lock", exec_dir=file_path.parent)


def run_updater(paths: list[str]) -> None:
    for path in paths:
        _run_updater_in_path(path)
