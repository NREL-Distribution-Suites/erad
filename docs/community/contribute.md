

# Contributing to ERAD

We welcome contributions from the community! Please follow these steps to get started.

## Developer Mode Installation

To install ERAD in development mode, clone the repository and install the dependencies using pip in a new environment:

```shell
git clone https://github.com/NLR-Distribution-Suite/erad.git
cd erad
pip install -e[dev,doc] .
```

This will install ERAD in editable mode, allowing you to make changes to the source code and have them reflected immediately.

## Running Tests Locally

To run the test suite locally, use the following command from the root of the repository:

```shell
pytest tests/
```

This will execute all tests in the `tests/` directory and report the results. Make sure you have installed all development dependencies before running the tests.

## Building Documentation Locally

To build the documentation locally, ensure you have installed the required dependencies:

```bash
pip install -e[doc] .
```

Then, from the root of the repository, run:

```bash
jupyter-book build docs/
```

The generated HTML documentation will be available in `docs/_build/html/`. Open `index.html` in your browser to view the documentation.

## Opening Issues and Feature Requests

* Use the **Issues** tab on GitHub to report bugs or request features.
* Include as much detail as possible (steps to reproduce, expected vs actual behavior, version info).
* For feature requests, describe the motivation and potential use cases.

## Submitting Pull Requests

1. Fork the repository and create a new branch:

   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Follow the existing coding style and linting rules:

   Linting and styling are enforced using [pre-commit](https://pre-commit.com/) hooks, configured in the repository's `.pre-commit-config.yaml` file.

   To set up pre-commit, run:

   ```bash
   pip install pre-commit
   pre-commit install
   pre-commit run --all-files
   ```
3. Commit your changes with clear, descriptive messages.
4. Push your branch and open a pull request on GitHub.
5. Run the test suite locally before submitting your pull request:

   ```bash
   pytest tests/
   ```
   Ensure all tests pass to maintain code quality.

6. For any new feature addition, ensure complete test coverage. Add or update tests to cover all new functionality and edge cases before submitting your pull request.
7. Ensure that documentation is updated to reflect any changes, new features, or modifications. Update relevant docstrings, markdown files, and user guides as needed.
8. Participate in the review process — address feedback promptly.



