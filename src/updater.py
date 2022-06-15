#! /usr/bin/env python
import os
from pathlib import Path

import shpyx
import tomlkit
import tomlkit.exceptions

"""Poetry configuration file name"""
POETRY_CONFIG_FILE_NAME = "pyproject.toml"


def _run_updater_in_path(path: str) -> None:
    """
    Run the updater in the specified path.
    """
    # Iterate over all files in the directory
    for root, _dirs, files in os.walk(path, topdown=False):
        for name in files:
            # Skip non Poetry configuration files.
            if name != POETRY_CONFIG_FILE_NAME:
                continue

            # Get the contents of the configuration file.
            file_path = Path(root).joinpath(name)
            file_contents = open(file_path).read()
            parsed_contents = tomlkit.parse(file_contents)

            # Get the poetry configuration.
            try:
                poetry_section = parsed_contents["tool"]["poetry"]
            except tomlkit.exceptions.NonExistentKey:
                # Skip if there is no poetry section.
                continue

            # Update the lock file, creating it if needed.
            shpyx.run("poetry update --lock", exec_dir=root)

            # Get all the outdated packages.
            results = shpyx.run("poetry show -o --no-ansi", exec_dir=root)

            if results.stdout == "":
                # Nothing to update.
                continue

            # Update the file contents, for each outdated package.
            for result in results.stdout.strip().split("\n"):
                # Remove the "(!)" decoration used to mark packages as non installed.
                result = result.replace(" (!) ", " ")

                # Get the package details.
                package_name, installed_version, new_version = result.split()[:3]

                # Update the package version in the file.
                for section in ("dependencies", "dev-dependencies"):
                    try:
                        package_details = poetry_section[section][package_name]
                    except tomlkit.exceptions.NonExistentKey:
                        # The section is not found in this file.
                        continue

                    print(f"Updating {package_name}: {installed_version} -> {new_version}")

                    # Replace the old version of the package with the new one.
                    if isinstance(package_details, str):
                        poetry_section[section][package_name] = new_version
                    else:
                        poetry_section[section][package_name]["version"] = new_version

            # Write the updated configuration file.
            open(file_path, "w").write(parsed_contents.as_string())

            # Finally, regenerate the lock file again, with the new package versions.
            shpyx.run("poetry update --lock", exec_dir=root)


def run_updater(paths: list[str]):
    for path in paths:
        _run_updater_in_path(path)
