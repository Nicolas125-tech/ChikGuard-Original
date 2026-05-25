# Contributing to ChikGuard

Thank you for your interest in contributing! 🐔

## Getting Started

1. **Fork** the repository and create your branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. Make your changes following the project structure.

3. **Test** your changes before submitting:
   ```bash
   python -m pytest backend/tests -q
   ```

4. **Commit** with a clear, conventional message:
   ```
   feat(vision): add thermal anomaly detection plugin
   fix(api): correct RBAC permission check on /api/accounts
   docs(readme): update quick start instructions
   ```

5. Open a **Pull Request** with a clear description of what you changed and why.

## Code Style

- **Python**: Follow PEP 8. Use `black` for formatting and `ruff` for linting.
- **JavaScript/JSX**: Follow ESLint config in `frontend/eslint.config.js`.
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/).

## Plugin Development

To add a new AI plugin, see the Plugin System section in the [README](README.md).
Place your plugin in `backend/plugins/<plugin-name>/plugin.py` and expose a `register()` function.

## Reporting Bugs

Use the [GitHub Issues](../../issues) page. Please include:
- OS and Python/Node version
- Steps to reproduce
- Expected vs actual behavior
- Logs if applicable

## Feature Requests

Open an issue with the `enhancement` label and describe your use case.

## Code of Conduct

Be respectful and constructive. We're all here to build something useful for farmers and agritech.
