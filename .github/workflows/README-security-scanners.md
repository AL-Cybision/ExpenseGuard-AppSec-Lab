# Security scanner learning notes

This file intentionally documents the purpose of the CI security checks so the lab can distinguish overlapping controls.

- **Semgrep**: SAST for insecure source-code patterns and data-flow issues.
- **SonarQube**: static analysis, security/reliability/maintainability findings, coverage and quality-gate concepts.
- **Gitleaks**: secret detection for credentials and tokens accidentally committed to the repository or Git history.
- **pip-audit**: Software Composition Analysis (SCA) for known vulnerabilities in Python dependencies declared in `requirements.txt`.
- **Dependabot**: continuous dependency-update monitoring for Python packages and GitHub Actions.

Scanner output must be triaged rather than accepted blindly. For each finding, determine whether it is reachable/applicable, identify the vulnerable component or source-to-sink path, decide true positive vs false positive, remediate or document an exception, and re-run the relevant check.
