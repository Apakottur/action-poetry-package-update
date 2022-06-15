# Update Python Poetry packages

A GitHub action that creates a pull request that updates the Python packages in
your [Poetry](https://python-poetry.org/) configuration files to the latest possible versions.

The action will:

1. Find all Poetry configuration files in the repository.
2. Bump all Python packages to their latest versions.
3. Create a pull request with the changes.

### Motivation

It is considered best practice to pin package versions in any production project, to ensure consistent applications.

For example, a Poetry configuration file might look like this:

```toml
[tool.poetry]
name = "package"
version = "1.0.0"
description = ""
authors = []

[tool.poetry.dependencies]
python = "^3.10"
shpyx = "0.0.13"
sqlalchemy = { extras = [
  "postgresql",
  "postgresql_asyncpg"
], version = "1.4.36" }

[tool.poetry.dev-dependencies]
mypy = "0.950"
```

All the packages are fixed to a specific version, which guarantees deterministic behavior.
At some point we might want to check if some of the packages that we're using have newer versions. We can do that by
running `poetry show -o` which will output something like this:

```text
mypy       0.950  0.961  Optional static typing for Python
shpyx      0.0.13 0.0.14 Configurable shell command execution in Python
sqlalchemy 1.4.36 1.4.37 Database Abstraction Library
```

We can then update the package versions in our `toml` file and run `poetry lock` or `poetry update` to regenerate the
lock file.

This action automates this whole process.

## Usage

Create the following workflow:

```yml
name: Update Python Poetry packages

on:
  # Allow manual triggers.
  workflow_dispatch:

  # Automatically run once a week.
  schedule:
    - cron: "0 7 * * MON"

jobs:
  update-packages:
    runs-on: ubuntu-latest
    steps:
      - uses: Apakottur/action-poetry-package-update@v1 # Can also be `@main`
        with:
          base-branch: main # Can also be `master`, for example.
```

This workflow creates a PR which bumps all Python packages in poetry configuration files to their latest versions.
The workflow can be triggered manually and will also run automatically once a week.

### Action inputs

All inputs are **optional**. If not set, sensible defaults will be used.

| Name             | Description                            | Default                                                                                                                          |
| ---------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `python-version` | Python version.                        | `3.10`.                                                                                                                          |
| `poetry-version` | Poetry version.                        | `1.1.13`.                                                                                                                        |
| `base-branch`    | Base branch for the updater to run on. | `main`.                                                                                                                          |
| `pr-body`        | The body of the pull request.          | `Automated changes by [update-python-poetry-packages](https://github.com/Apakottur/action-poetry-package-update) GitHub action`. |

### Action outputs

None

## License

[MIT](LICENSE)
