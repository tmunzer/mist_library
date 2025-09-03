Thank you for contributing to the mist_library repository.

This document explains how to get started, how to report issues, and the expectations for pull requests so changes are safe, testable and easy to review.

## Quick start (local)

1. Fork the repository and create a feature branch from `master`:

   - Use a short, descriptive branch name: `fix/<area>-<short-desc>` or `feat/<area>-<short-desc>`.

2. Create and activate a Python virtual environment (macOS/Linux):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Run a script's help to confirm the environment is working:

```bash
python scripts/orgs/org_conf_deploy.py -h
```

## Environment / secrets

- The repository's scripts expect an environment file (default `~/.mist_env`).
- Never commit credentials, tokens, or secret files to the repository or a PR. Remove them from diffs immediately if accidentally included and rotate the credentials.
- If you need to demonstrate a flow, provide a sanitized example env file (see README for an example) and avoid real tokens.

## Reporting issues

When opening an issue, include:

- A short, descriptive title.
- Steps to reproduce the problem or exact command you ran.
- The script path and line number (if applicable).
- Your Python version and `mistapi` version (run `python3 -c "import mistapi; print(mistapi.__version__)"`).
- Relevant, sanitized logs or error messages.

Good issues are reproducible and include minimal data necessary for debugging.

## Pull requests (PRs)

Best practices for PRs:

- One logical change per PR.
- Keep PRs small and focused.
- Include tests or a short smoke-check when you change behavior.
- Update `README.md` or script header docstrings when you change behavior or add new scripts.
- Update or add `MISTAPI_MIN_VERSION` in script headers if the change requires a newer `mistapi` version.
- If a change may be destructive (mass deletes, claims), require a CLI `--dry-run` first and document risks in the PR description.

Suggested PR checklist (include in the PR description):

- [ ] I have run the relevant script(s) locally and verified the change (or added a smoke test).
- [ ] There are no credentials in the diff.
- [ ] I updated the README or script header where applicable.
- [ ] I updated `MISTAPI_MIN_VERSION` in scripts that require a newer mistapi.
- [ ] I added tests or a reproducible example for non-trivial logic.

## Coding style and tests

- Language: Python 3.8+ (some scripts assume newer language features; prefer 3.10+).
- Keep changes consistent with existing code style (short, well-documented CLI scripts). Use type hints where appropriate.
- Add or update docstrings at the top of script files explaining the purpose, options and example calls.
- Where practical, include a small unit test or a smoke test (follow the repository's existing patterns). If you add tests, include the commands to run them in the PR.

## Logging and debug output

- Many scripts use numeric logging levels (e.g., `CONSOLE_LOG_LEVEL`, `LOGGING_LOG_LEVEL`). Preserve those options when editing scripts.
- Avoid printing sensitive data to logs.

## Adding new scripts

When adding a new script, follow these guidelines:

- Place the script in the appropriate `scripts/` subfolder.
- Add a clear module-level docstring with purpose, usage examples and the default `ENV_FILE` value (e.g., `ENV_FILE = "~/.mist_env"`).
- If the script depends on specific `mistapi` features, include `MISTAPI_MIN_VERSION = "x.y.z"` near the top.
- Provide at least one usage example in the header and verify `-h` output is helpful.
- Add the script to the `README` index or propose `SCRIPTS_INDEX.md` generation if the list becomes large.

## Security and sensitive operations

- Mark destructive changes in the PR title and description (e.g., `dangerous`, `destructive`) and provide a dry-run mode.
- If a change can modify many objects in a Mist org, include a clear rollback or validation strategy in the PR.

## Licensing and copyright

- The project is licensed under the MIT License. By contributing you agree that your contribution can be distributed under the repository license.

## Maintainers and reviews

- PRs are reviewed on GitHub. Expect maintainers to ask for small, incremental improvements during review.
- If you want to take on larger work (refactor, test-suite addition), open an issue first describing scope and plan.

---

Thanks for contributing — clear, small PRs with examples and no secrets make reviews fast and safe.
