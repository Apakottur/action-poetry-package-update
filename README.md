# Update Python Poetry packages

A Github action that creates a pull request that updates the Python packages in 
your [Poetry](https://python-poetry.org/) configuration files to the latest possible versions.

The action will:

1. Find all poetry configuration files in the repository.
2. Bump all Python packages to their latest versions.
3. Creaete a pull request with the changes.

## Usage

Create the following workflow:
```yml
name: Update Python Poetry packages 

on:
  workflow_dispatch:

jobs:
  updater:
    runs-on: ubuntu-latest
    steps:
      - uses: Apakottur/action-poetry-package-update@v1
        with:
          base-branch: main # Can also be `master`, for example.
```

This workflow can be triggered manually at any time, creating a PR which bumps all Python packages in poetry
configuration files.

### Action inputs

All inputs are **optional**. If not set, sensible defaults will be used.

| Name             | Description                            | Default               |
|------------------|----------------------------------------|-----------------------|
| `base-branch`    | Base branch for the updater to run on. | Defaults to `main`.   |
| `python-version` | Python version.                        | Defaults to `3.10`.   |
| `poetry-version` | Poetry version.                        | Defaults to `1.1.12`. |



### Action outputs

None

## License

[MIT](LICENSE)