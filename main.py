#! /usr/bin/env python
import os
from pathlib import Path

import shpyx

POETRY_CONFIG_FILE_NAME = "pyproject.toml"


def main():
    for root, dirs, files in os.walk(".", topdown=False):
        for name in files:
            if name != POETRY_CONFIG_FILE_NAME:
                continue

            # Get the contents of the existing poetry configuration file.
            file_path = Path(root).joinpath(name)
            file_contents = open(file_path).read()

            # Verify that there is a poetry section
            if "[tool.poetry]" not in file_contents:
                continue

            # Update the lock file, creating it if needed.
            shpyx.run("poetry update --lock", exec_dir=root)

            # Get all the outdated packages.
            results = shpyx.run("poetry show -o --no-ansi", log_output=True, exec_dir=root)

            # Update the file contents, for each outdated package.
            for result in results.stdout.strip().split("\n"):
                # Remove the "(!)" decoration used to mark packages as non installed.
                result = result.replace("(!)", "")

                # Get the package details.
                package_name, installed_version, new_version = result.split(" ")[:3]

                # Replace the package version, supporting both single and double quotes.
                file_contents = file_contents.replace(
                    f"{package_name} = '{installed_version}'",
                    f"{package_name} = '{new_version}'",
                )
                file_contents = file_contents.replace(
                    f'{package_name} = "{installed_version}"',
                    f'{package_name} = "{new_version}"',
                )

            # Write the updated configuration file.
            open(file_path, "w").write(file_contents)

            # Finally, regenerate the lock file again, with the new package versions.
            shpyx.run("poetry update --lock", log_output=True, exec_dir=root)


if __name__ == "__main__":
    main()
