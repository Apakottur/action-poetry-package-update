import functools
import os
from pathlib import Path

import shpyx
import tomlkit
import tomlkit.exceptions

"""Poetry configuration file name"""
POETRY_CONFIG_FILE_NAME = "pyproject.toml"

"""Sections in the Poetry configuration files where dependencies reside"""
SECTIONS = ("dependencies", "dev-dependencies")


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
            pairs_to_check = list(poetry_section.items())
            while pairs_to_check:
                current_pair = pairs_to_check.pop()
                if current_pair[0] in SECTIONS:
                    current_section = current_pair[1]
                elif isinstance(current_pair[1], dict):
                    pairs_to_check.extend(current_pair[1].items())
                    continue
                else:
                    continue

                for details in current_section.values():
                    if "path" in details:
                        file_path_to_deps[file_path.resolve()].append((Path(root) / details["path"] / name).resolve())

    # Order the projects based on interdependencies, where dependencies go first.
    def cmp(x: Path, y: Path) -> int:
        if x in file_path_to_deps[y]:
            # X is a dependency of Y, mark it as smaller, so it appears first in the list.
            return -1
        else:
            return 1

    file_paths_in_order = sorted(file_path_to_deps, key=functools.cmp_to_key(cmp))

    # Second iteration - make sure all projects have lock files.
    for file_path in file_paths_in_order:
        shpyx.run("poetry lock", exec_dir=file_path.parent)

    # Third iteration - run updates in order.
    for file_path in file_paths_in_order:
        # Get the contents of the configuration file.
        file_contents = Path(file_path).read_text()
        parsed_contents = tomlkit.parse(file_contents)
        poetry_section = parsed_contents["tool"]["poetry"]

        print(f"TOML contents of {file_path}: {parsed_contents}")

        # Construct the poetry command to get outdated packages.
        poetry_cmd = "poetry show -o --no-ansi"
        if group_section := parsed_contents["tool"]["poetry"].get("group"):
            poetry_cmd += f" --with {','.join(group_section.keys())}"

        # Get all the outdated packages.
        results = shpyx.run(poetry_cmd, exec_dir=file_path.parent)

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
            pairs_to_check = list(poetry_section.items())
            while pairs_to_check:
                current_pair = pairs_to_check.pop()
                if current_pair[0] in SECTIONS:
                    current_section = current_pair[1]
                elif isinstance(current_pair[1], dict):
                    pairs_to_check.extend(current_pair[1].items())
                    continue
                else:
                    continue

                try:
                    original_package_name, package_details = next(
                        (name, details)
                        for name, details in current_section.items()
                        if name.lower() == package_name.lower()
                    )
                except StopIteration:
                    # The package is not in this section.
                    continue

                if isinstance(package_details, str):  # noqa: SIM108
                    written_version = package_details
                else:
                    written_version = package_details["version"]

                # Skip packages that are locked via the '==' operator.
                if written_version.startswith("=="):
                    print("Skipping locked package:", package_name)
                    continue

                print(f"Updating {package_name}: {installed_version} -> {new_version}")

                # Replace the old version of the package with the new one.
                if isinstance(package_details, str):
                    current_section[original_package_name] = new_version
                else:
                    current_section[original_package_name]["version"] = new_version

        # Write the updated configuration file.
        Path(file_path).write_text(parsed_contents.as_string())

        # Finally, regenerate the lock file again, with the new package versions.
        shpyx.run("poetry update --lock", exec_dir=file_path.parent)


def run_updater(paths: list[str]) -> None:
    for path in paths:
        _run_updater_in_path(path)
