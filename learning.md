# Learning — ExpenseGuard AppSec & DevSecOps

> **Living learning notebook / source of truth for concepts.** Updated: **2026-10-07**. This records what we learned, why it matters, and what is **implemented versus planned**. For onboarding and diagrams, see [README.md](README.md). For the real state of CI, consult the [GitHub Actions runs](https://github.com/AL-Cybision/ExpenseGuard-AppSec-Lab/actions); a green workflow can contain a skipped scanner.
>
> **Learning rule:** For each control, explain **problem → attacker scenario → implementation → verification → remaining risk**. A scanner alert is a lead to investigate, not proof of exploitability; a passing scan is not proof of security.

## 1. Git, GitHub, and change tracking

- **Working tree → staging → local commit → push:** `git add` selects content; `git commit` records a snapshot **locally**; `git push` publishes local commits to GitHub and advances the remote branch.
- **GitHub API edits:** Updating a file using GitHub's Contents API creates a commit **on the remote branch directly**. There is **no separate push**; local clones need `git pull --ff-only` to catch up. Our README was updated this way.
- **`git fetch`** updates remote-tracking references without changing the working files. **`git status -sb`** shows current branch and ahead/behind status; **`git log -1 --oneline`** shows HEAD.
- **Branch / PR:** A branch isolates changes; a pull request (PR) requests review and merging. A **commit** is a versioned snapshot; a **push** transfers local commits; a **merge** combines history.
- **Verified example:** The README change `e93c4b2` exists on GitHub's `learning/authentication-fundamentals` branch; it was not only a local commit.

## 2. AppSec, DevSecOps, and the CI/CD pipeline

- **AppSec:** Security across requirements, design, code, dependencies, tests, release and operations—not just finding web vulnerabilities.
- **CI:** Continuous integration runs automated checks for pushed code and PRs. **CD:** Continuous delivery/deployment prepares/releases tested artifacts. **ExpenseGuard has CI checks, not a CD/deployment system yet.**
- **Unit tests:** Verify individual expected behavior. **Security regression tests:** Prove an abuse case remains denied, e.g., a manager cannot approve their own expense and denial causes no side effect.
- **SAST (Semgrep):** Reads source and configuration without running the app; flags risky patterns/data flow and IaC/CI configuration. Review attacker control, source/sink, reachability and existing controls.
- **SCA (pip-audit, Semgrep Supply Chain):** Finds known advisories in third-party dependencies. **Direct** = explicitly declared (FastAPI, pytest); **transitive** = installed through another package (Starlette via FastAPI). CVE presence does not guarantee the affected feature is reachable.
- **Secret scan (Gitleaks):** Searches for committed credentials; full Git history matters. If a real key was committed, **revoke/rotate it**, even if later deleted from the current file.
- **Docker build (implemented):** Packages the app, runtime and dependencies into an executable image. A successful build proves it built, not that it is secure.
- **Container scan (Trivy, implemented):** Scans the **built image** for vulnerable OS and application packages; image scanning complements source SCA.
- **IaC scan (Checkov / Trivy IaC, planned):** Scans infrastructure definitions (e.g., public database, wildcard IAM, public S3, unencrypted resources).
- **SBOM (Trivy, implemented):** Software Bill of Materials: component inventory. ExpenseGuard now emits CycloneDX 1.6; it helps identify affected artifacts after new advisories, but an SBOM is not itself a security scan or fix.
- **DAST (OWASP ZAP, planned):** Tests the **running** API over HTTP. Dynamic behavior differs from SAST's source inspection; authenticated coverage and safe staging matter.
- **Security gate:** CI checks can fail on defined risks; a **required status check / branch rule** must be configured to actually prevent merging. Separate **finding severity**, business risk and exploitability. Do not make every low-confidence alert a permanent blocker.
- **Exception / risk acceptance:** Document finding, cause, environment, compensating controls, owner, approver and expiration; recheck later. Suppressing an alert silently is **not** risk acceptance.
- **Parallel execution:** Existing ExpenseGuard GitHub Actions run as **separate workflows**, not as the future linear build → scan → deploy pipeline.

### Verified CI state (latest milestones checked through 2026-10-07)

| Check | What was observed | Important limit |
| --- | --- | --- |
| Pytest / Python 3.12 | **36 passed** | A regression suite is not a full penetration test. |
| pip-audit | **No known vulnerabilities found** for resolved requirements | Depends on advisory data and evaluated dependencies at scan time. |
| Gitleaks | **Workflow passed** | No guarantee every possible credential was recognized. |
| Semgrep GitHub CI | **Operational**; verified Oct 3 authenticated run reported 0 findings | Zero findings on one revision is not proof the application is secure. |
| SonarQube workflow | **Workflow passed; actual SonarQube scan skipped** | Requires `SONAR_TOKEN` and project/organization variables before counting it as operational. |
| Container Security | **Build + hardened smoke test + Trivy + SBOM passed** at `cfbcc70` | Full Trivy report still contained 171 findings; the gate passed because no HIGH/CRITICAL finding had a fix available. |

## 3. Three supply-chain decisions we implemented

### Why pin GitHub Actions to full 40-character SHAs?

`uses: actions/checkout@v6` uses a **movable tag**. If its target changes (e.g., compromised publisher), the same workflow YAML might execute different code. `uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803` selects a **specific commit**. In GitHub's conventional SHA-1 Git object format, **160 bits ÷ 4 bits/hex digit = 40 hexadecimal characters**. SHA is a **content identifier, not encryption or a secret**. Verify provenance and review the chosen Action: immutable code can still be malicious. Pinning also **stops automatic updates**; review new commits using Dependabot.

### Why a seven-day Dependabot cooldown?

`.github/dependabot.yml` contains `cooldown: { default-days: 7 }` for both **pip** and **github-actions**. A brand-new ordinary version release is skipped until it is at least seven days old, reducing immediate exposure to potentially compromised fresh releases. **This applies to version updates, not Dependabot security updates.** GitHub's ordinary default is three days; ours is seven. Dependabot still checks on the **weekly schedule**, so "day seven" means eligible at the next check, not an exactly timed PR. Tradeoff: routine bug fixes also arrive later; review urgent fixes explicitly.

### What is the Starlette pin, and why was it added?

- `fastapi==0.142.2` / `starlette==1.6.0` / `pytest==9.0.3` use `==` to select **exact package versions**. Starlette supplies lower-level web/ASGI functionality **used by FastAPI**; it is normally a **transitive dependency**.
- We upgraded FastAPI so newer patched Starlette versions were compatible, then explicitly pinned Starlette to a reviewed version to close an SCA finding. **Compatibility was tested** (36 tests passed; pip-audit clean at that checkpoint).
- **Important nuance:** [FastAPI's own versioning guide](https://fastapi.tiangolo.com/deployment/versions/) generally advises **against directly pinning Starlette**; let FastAPI declare its compatible range. Our direct pin was a **targeted remediation**, not universal best practice. A better long-term practice is to declare actual direct dependencies deliberately and use a reviewed **complete lock file with hashes** for repeatable resolved builds.
- **Difference:** A **version pin** selects a package release, a **commit-SHA pin** selects Git code, and a **lock file** records the full resolved dependency graph. None automatically prove package trustworthiness.

## 4. Container security — what we just implemented

- **Insecure vs hardened image:** `Dockerfile.insecure` intentionally uses a floating base, root execution, broad copy and development dependencies. The default `Dockerfile` is the deployable path.
- **Base-image digest pinning:** `python:3.12.15-slim-trixie@sha256:...` keeps a readable tag but Docker selects the immutable manifest digest. This prevents a mutable tag from silently changing our base image; the digest must still be reviewed/upgraded for security patches.
- **Multi-stage build:** dependencies are prepared in a builder stage and only runtime files are copied to the final stage. This reduces build tooling and attack surface in the shipped image.
- **Runtime vs dev dependencies:** `requirements-runtime.txt` contains only packages the API needs. `requirements.txt` adds pytest/httpx/coverage for development. Test tools should not be present in production just because CI needs them.
- **`.dockerignore`:** keeps Git metadata, virtualenvs, tests, local environment files, private-key/certificate patterns and other unnecessary files out of the Docker build context. It reduces accidental inclusion; it is not a substitute for secret management.
- **Non-root user:** image runs as UID/GID 10001. Root inside a container is not automatically host root, but removing unnecessary root privilege reduces impact if the application is compromised.
- **Read-only filesystem:** CI runs the image with `--read-only` and only an explicit temporary `/tmp` filesystem. This limits persistence/tampering paths.
- **Capabilities and privilege:** `--cap-drop=ALL` and `no-new-privileges` reduce kernel privileges available to the process. Resource limits cap PIDs, memory and CPU.
- **Health check:** confirms the service actually reaches a useful running state; it is an availability/operation signal, not a security proof.
- **Trivy result (2026-10-07, `cfbcc70`):** 171 total findings = 62 LOW + 63 MEDIUM + 44 HIGH + 2 UNKNOWN + 0 CRITICAL. The 44 HIGH findings had no fixed version in the report. Our blocking gate ignores unfixed items and fails only on **fixable HIGH/CRITICAL** vulnerabilities; the full JSON report still records everything.
- **Why that gate?** A policy that blocks on vulnerabilities with no upstream fix can permanently stop delivery without offering an actionable remediation. We still triage/track them, while fixable HIGH/CRITICAL findings block. This is a policy choice that should change with threat model, exposure and organizational risk appetite.
- **SBOM evidence:** Trivy generated **CycloneDX 1.6 with 113 components**. The SBOM and full JSON vulnerability report are uploaded as a short-lived CI artifact.
- **Big lesson:** **green CI ≠ zero vulnerabilities**. Green means the current policy was satisfied. Always read what the policy actually gates.

## 5. IAM, authentication, and authorization in ExpenseGuard

- **IAM (identity and access management):** Who are the actors, how are they authenticated, and which resources/actions are permitted?
- **Principal:** Identity (e.g., a user). **Subject:** Principal in the context of the *current validated session*. **Authentication (AuthN):** Prove identity; **authorization (AuthZ):** Decide which action on which resource is allowed.
- **RBAC:** Assign permissions to roles (`employee`/`manager`/`admin`). **ABAC:** Consider attributes such as department, owner and status. **DAC:** Owner-driven discretion; **MAC:** Centrally enforced security classifications; useful models but not the primary ExpenseGuard policy.
- **PDP / PEP:** Policy Decision Point evaluates allow/deny; Policy Enforcement Point prevents a disallowed action. ExpenseGuard calls `authorize(...)` **before** modifying expense status.
- **Least privilege:** Give only necessary access. **Default deny:** Unrecognized actions fail. **Separation of duties (SoD):** A manager cannot approve their own expense. **JIT/JEA:** Time-limited access / only enough privilege for a specific task (concepts, not implemented features).
- **Password hashing:** Use slow, salted **Argon2id** for passwords, never plain SHA-256. An unknown username triggers a dummy password-hash check to reduce obvious enumeration timing differences.
- **Opaque bearer session:** Generate a cryptographically random token; return raw token to the client **once**; keep only its SHA-256 hash on the server (appropriate for high-entropy random tokens). Check token existence, expiry, revocation, account activity; logout revokes. Never accept `X-User-ID` as identity.
- **401 vs 403:** 401 = no valid authentication; 403 = authenticated but permission denied. **BOLA/IDOR:** Changing `/expenses/102` to another person's ID must not bypass object-level checks.
- **API6 (unrestricted access to sensitive business flows) vs BOLA:** With BOLA the attacker accesses an **unauthorized object**; API6 may abuse a **legitimately accessible workflow** at harmful scale or in an unintended sequence (e.g., automated mass purchases). Rate limits, anti-automation and business-flow controls complement AuthZ.
- **Not yet implemented:** Password reset and secure reset links, tenant isolation, MFA enforcement, OAuth/OIDC token validation and production persistence. **Host-header poisoning** matters for password reset: never derive a sensitive reset URL from an untrusted HTTP Host header; use an approved canonical origin.

## 6. Threat modeling, secure development, and the cloud roadmap

- **Asset:** What needs protection (account, expense, receipt, credentials). **Actor/entry point:** Who can interact and where (client → API, GitHub → Actions, app → cloud services). **Trust boundary:** Where untrusted input crosses into a privileged component.
- **DFD (data-flow diagram):** Shows systems, processes, data stores and flows. **STRIDE:** Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege. Add abuse cases, risk owners and mitigations.
- **Secure code review:** Trace **source → transformations/validation → sensitive sink**; assess controls and reachability. Write developer-friendly findings: scenario, root cause, severity rationale, secure fix, regression test and verification.
- **SSDLC:** Security requirements, design review, PR checklist, tests, release gates, production logging, vulnerability response and time-limited exception handling across the software lifecycle.
- **Container hardening (implemented baseline):** Digest-pinned slim Python base, multi-stage build, runtime-only dependencies, `.dockerignore`, non-root user, read-only runtime test, dropped capabilities, no-new-privileges, resource limits, health check, Trivy report and CycloneDX SBOM.
- **AWS target (not deployed):** Internet → public ALB → private ECS Fargate (FastAPI) → private RDS PostgreSQL; S3 for receipts, Secrets Manager for credentials, ECR for images, CloudWatch for application logs and CloudTrail for AWS API auditing.
- **AWS IAM:** Roles, policies and trust relationships determine *who can assume a role* and *what the role can do*. Aim for temporary credentials; **GitHub OIDC → restricted AWS deployment role** instead of long-lived AWS keys.
- **Terraform/IaC (planned):** Infrastructure stored/reviewed as code. Check public network exposure, permissive security groups, wildcard IAM, missing encryption/logging and hardcoded secrets. Run `terraform validate` and `terraform plan` before any approved `apply`; obtain cost approval first.
- **Why ECS before Kubernetes?** Prioritize application/cloud IAM and deployment boundaries without taking on a cluster-management project. Kubernetes RBAC/service accounts/NetworkPolicy/pod security are **stretch topics**.
- **AI Product Security (later):** Optional policy assistant gives realistic prompt-injection, RAG cross-tenant leakage, unauthorized tool actions and retrieval poisoning scenarios; not a current feature.

## 7. Quick reference / next learning steps

~~~text
Current:    Local FastAPI + demo memory store + tested AuthN/AuthZ
CI passing: Pytest / Gitleaks / pip-audit / authenticated Semgrep
Container:  hardened Docker build + Trivy report + CycloneDX SBOM + fixable HIGH/CRITICAL gate
CI pending: real SonarQube scanner configuration; broader required-check policy
Next:      threat modeling + SSDLC, then Terraform/IaC + AWS/IAM
Later:     secure app features / tenant isolation / DAST / optional AI security
~~~

Useful commands (inside the project directory):

~~~bash
git status -sb                                  # local/remote branch status
git log -1 --oneline                            # current local commit
git fetch origin --prune                        # update remote refs only
git pull --ff-only origin learning/authentication-fundamentals
python -m pip check                             # dependency conflicts
python -m pytest -q                             # regression tests
~~~

**Verification principle:** Answer four interview questions for every claimed skill: **What did I build? What could go wrong? What control did I implement? What evidence shows it worked?**

### Primary references

- [GitHub: Secure use of Actions (SHA pinning)](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub: Dependabot cooldown options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
- [GitHub: How Dependabot version updates work](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-version-updates)
- [FastAPI: Version pinning and Starlette guidance](https://fastapi.tiangolo.com/deployment/versions/)

**Notebook convention:** Append short, verified lessons after each milestone. Label **implemented**, **tested**, and **planned** honestly; revise dated status claims rather than presenting them as permanent truths.
