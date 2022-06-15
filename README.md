# Update Python Poetry packages

A Github action that creates a pull request that updates the Python packages in 
your [Poetry](https://python-poetry.org/) configuration files to the latest possible versions.

The action will:

1. Find all poetry configuration files in the repository.
2. Bump all Python packages to their latest versions.
3. Create a pull request with the changes.

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
      - uses: Apakottur/action-poetry-package-update@v1
        with:
          base-branch: main  # Can also be `master`, for example.
```

This workflow creates a PR which bumps all Python packages in poetry configuration files to their latest versions.
The workflow can be triggered manually and will also run automatically once a week.

### Action inputs

All inputs are **optional**. If not set, sensible defaults will be used.

| Name             | Description                            | Default                                                                                                                          |
|------------------|----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| `python-version` | Python version.                        | `3.10`.                                                                                                                          |
| `poetry-version` | Poetry version.                        | `1.1.13`.                                                                                                                        |
| `base-branch`    | Base branch for the updater to run on. | `main`.                                                                                                                          |
| `pr-body`        | The body of the pull request.          | `Automated changes by [update-python-poetry-packages](https://github.com/Apakottur/action-poetry-package-update) GitHub action`. |



### Action outputs

None

## License

[MIT](LICENSE)

## TODO
1. Add `paths` input to accept only specific paths.
2. Add `include_fixed` input to configure whether fixed packages should be updated.
3. Add unit tests.
4. Add further motivation and examples in the README