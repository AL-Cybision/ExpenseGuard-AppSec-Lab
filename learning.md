# Learning — ExpenseGuard AppSec & DevSecOps

> **Living learning notebook / source of truth for concepts.** Updated: **2026-10-08**. This records what we learned, why it matters, and what is **implemented versus planned**. For onboarding and diagrams, see [README.md](README.md). For the real state of CI, consult the [GitHub Actions runs](https://github.com/AL-Cybision/ExpenseGuard-AppSec-Lab/actions); a green workflow can contain a skipped scanner.
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

## 4. Docker and container security — concepts, decisions, evidence

> **Status:** Hardened image, Trivy scan, CycloneDX SBOM and CI smoke test are **implemented**. The following is our learning reference for **what**, **why**, **where configured**, **how verified**, and **remaining risks**. Docker hardening is not a substitute for fixing application vulnerabilities.

### 4.1 Image, container and Python slim: what runs where?

- **Dockerfile:** Instructions to construct an image. **Image:** A packaged filesystem and configuration (base OS userspace, Python, installed packages, app, startup command), not a running process. **Container:** A running/created instance of an image. One image can start multiple independent containers.
- A Linux container uses the **host's Linux kernel**; it is **not** a full VM with its own kernel. Namespaces, cgroups and other kernel features provide isolation, subject to configuration and host security.
- Our base is `python:3.12.15-slim-trixie`: **Debian Trixie slim userspace + Python 3.12.15** (not Ubuntu). The image includes the Python interpreter and supporting runtime libraries. **`slim`** means fewer extra OS packages/tools than the fuller Python image; smaller does not automatically mean secure or vulnerability-free.
- ExpenseGuard then adds FastAPI, Uvicorn, Argon2 and our `app/` package. Trivy's image scan checks known vulnerable components in the **built image** (OS and Python packages); it is **not** HTTP testing of `/auth/login` (that would be DAST).

```text
Dockerfile + filtered build context  --docker build-->  ExpenseGuard image
ExpenseGuard image                   --docker run---->  Running container(s)
Host Linux kernel                    <--------------->  Shared by those containers
```

### 4.2 Build context, `.dockerignore`, `COPY`, image layers and caching

- `docker build -t expenseguard:local .`: the final `.` chooses the current directory as **build context**. Docker can use included files when executing `COPY` or `ADD`.
- **`.dockerignore` filters the context before copying.** Our file excludes `.git`, `.venv*`, `.env*`, private-key patterns, tests, cache/coverage files and unnecessary project docs. It reduces accidental secret exposure and unnecessary transfer; **real secrets still must never enter the image**.
- `COPY . .` (in `Dockerfile.insecure`) copies broadly from the **already-filtered context** to the current image directory. The production Dockerfile copies **only** `requirements-runtime.txt` during the builder stage and **only** `app/` in the runtime stage. **`COPY app ./app`** is more deliberate than copying a whole repository.
- Image filesystem changes can be retained in **layers**. File-copy/install operations create layer content; some instructions such as `CMD` and `EXPOSE` primarily set metadata. Docker can reuse cached installation layers when application code changes but requirements do not.
- **Why copy requirements first?** `COPY requirements-runtime.txt ./` → `RUN pip install ...` → later `COPY app ./app`. Changing only app code should not invalidate the package-install layer; changing requirements should.
- **Layer secret pitfall:** `COPY .env /...` in one layer followed by `RUN rm ...` in another may hide the file from the final merged view but **not remove its bytes from underlying layers/history**. Prevent inclusion in the first place; use runtime secret injection or secure build-secret mounts when needed.

### 4.3 `FROM`, tags, digests and supply-chain reproducibility

- `FROM` selects the **base image**. Our exact build argument is `python:3.12.15-slim-trixie@sha256:ddb0207ae1f0356c2b724d740769b0c5f5f51cc54a0525178f721825f78fe74c`.
- **Tag** (`python:3.12-slim`): convenient **mutable reference** that may resolve to different image content later. **Digest** (`@sha256:...`): identifies the particular immutable image manifest; our readable tag plus digest selects the pinned artifact.
- Pinning improves change control/reproducibility but **does not install new security patches automatically** and does not make the image inherently trustworthy. Review new base-image releases/digests, rebuild, test and rescan.
- **Honest limitation:** An immutable base digest and top-level Python `==` pins do **not** create a fully reproducible dependency graph. Transitive dependencies and the builder's `pip install --upgrade pip` can still resolve differently. A reviewed complete lockfile/hashes and controlled build inputs remain future work.

### 4.4 Multi-stage build: builder versus runtime

Our `Dockerfile` uses the same slim Python base twice:

```dockerfile
FROM ${PYTHON_BASE} AS builder
WORKDIR /build
COPY requirements-runtime.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install --prefix=/install -r requirements-runtime.txt

FROM ${PYTHON_BASE} AS runtime
WORKDIR /app
COPY --from=builder /install/ /usr/local/
COPY --chown=10001:10001 app ./app
```

- **Builder:** Installs runtime Python packages under `/install`. **Runtime:** Starts fresh from the pinned base and copies only installed runtime dependencies and application code. The builder's intermediate filesystem is **not** itself the final runtime image.
- `requirements-runtime.txt` contains FastAPI, Starlette, Uvicorn and Argon2. `requirements.txt` includes that file plus `pytest`, `httpx` and `pytest-cov`. The production Dockerfile uses **only** the runtime file; test tooling should not be shipped unnecessarily.
- If future packages require compilers or build headers, install those **only in the builder**. **Current limitation:** The builder does not install extra compiler packages today, and the final Python slim runtime still contains some tooling from its base; multi-stage alone is not a guarantee of a minimal/distroless final image.
- **Why:** Minimize code/tools available after compromise, dependency exposure, artifact size and patching obligations—while retaining everything the service legitimately needs.

### 4.5 Least-privilege identity: `USER 10001:10001`

```dockerfile
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --create-home --home-dir /home/app \
       --shell /usr/sbin/nologin app
COPY --chown=10001:10001 app ./app
USER 10001:10001
```

- UID **0** is root. ExpenseGuard does not need root to execute Python or bind port **8000**. We create a stable dedicated non-root UID/GID **10001**; the number is a convention, **not a secret or special security token**.
- `--chown` gives the app user ownership of the copied app files; `nologin` marks the account as a service identity rather than an ordinary login account. Linux file access still depends on owner/group/mode and mount settings.
- **Post-exploitation reasoning:** RCE as root generally grants more in-container authority than RCE as a normal user. Non-root **reduces impact**, but does **not** fix the RCE, remove all attack options, or guarantee no container escape.
- **Evidence:** The container CI job inspects `docker image inspect ... --format '{{.Config.User}}'` and requires the value `10001:10001`.

### 4.6 Runtime defense in depth: filesystem, privileges and resources

Our **CI smoke test**, not the Dockerfile itself, supplies these runtime restrictions:

```bash
docker run -d \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop=ALL \
  --security-opt no-new-privileges=true \
  --pids-limit=100 \
  --memory=256m \
  --cpus=1.0 \
  -p 127.0.0.1:8000:8000 \
  expenseguard:local
```

| Control | Question answered | Benefit and limitation |
| --- | --- | --- |
| `USER 10001:10001` | **Who am I?** | Starts as non-root; does not eliminate code execution or unauthorized network requests. |
| `--read-only` | **What can I modify?** | Root filesystem is read-only at runtime, reducing tampering/persistence; other writable mounts may exist. |
| `--tmpfs /tmp:rw,noexec,nosuid,size=64m` | **Where may temporary writes occur?** | Small temporary writable `/tmp`; `noexec` restricts direct file execution, but is **not** a blanket code-execution prevention. |
| `--cap-drop=ALL` | **Which special Linux capabilities do I have?** | Removes Linux capabilities such as those associated with privileged administration; add back only a capability the service actually needs. |
| `no-new-privileges` | **Can execution grant additional privilege later?** | Prevents gaining new privileges through operations such as setuid transitions; doesn't remove privileges already held. |
| `--memory=256m` | **How much RAM?** | Limits memory; legitimate workloads can also hit the limit and be killed. |
| `--cpus=1.0` | **How much CPU time?** | Limits approximately one CPU's worth of capacity; not complete DoS protection. |
| `--pids-limit=100` | **How many tasks/processes?** | Helps contain process exhaustion/fork bombs; does not prevent all resource attacks. |

**Threat scenario:** If a vulnerable endpoint permits RCE, the attacker still runs code with the app's permissions and may access in-memory sessions or reachable network services. These controls make privileged operations and writes harder, **not impossible to cause harm**. Network controls, secure code, logging, safe secret access and API rate limits are separate layers.

**Deployment gap:** The immutable image enforces the default non-root `USER` and contains the `HEALTHCHECK`, but `--read-only`, capabilities, `no-new-privileges`, resource limits and loopback port mapping are **only proven in the CI `docker run`**. A future ECS task definition/deployment must explicitly translate/enforce appropriate equivalents; do not claim AWS production hardening exists.

### 4.7 Health checks, `EXPOSE` and network exposure

- `EXPOSE 8000` is **image metadata** describing the intended application port; it **does not publish the port** and is not an access-control firewall.
- `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` listens on interfaces **inside the container**. Runtime publication determines host reachability.
- `docker run -p 8000:8000 ...` generally publishes on all host interfaces. CI instead uses `-p 127.0.0.1:8000:8000` to bind on the host's **loopback interface** for its smoke test.
- The Dockerfile declares `HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3` and performs a Python `urllib.request` GET of `http://127.0.0.1:8000/health`. It distinguishes **running process** from **responding HTTP service**. CI additionally sends `curl` requests from the runner to validate that the service responds.
- **Limitations:** A passing `/health` currently does **not** prove the DB/identity store is ready; Docker marking a container unhealthy does **not by itself guarantee automatic restart**. For AWS, the planned design is Internet → ALB HTTPS/443 → private ECS task on 8000, not directly exposed container ports.

### 4.8 Trivy image scan, severity gates and SBOM — implemented baseline

- **Trivy full report:** Scan the **built image** for known OS/Python package vulnerabilities with all severities and `ignore-unfixed: "false"`; save `trivy-image.json` without failing that reporting step. A scanner finding requires triage, reachability analysis and remediation planning.
- **Blocking gate:** A separate scan selects **HIGH/CRITICAL**, sets `ignore-unfixed: "true"` and `exit-code: "1"`. In other words, it fails CI on **fixable** HIGH/CRITICAL findings, not every unfixed advisory.
- **Verified 2026-10-07 at `cfbcc70`:** **171 findings** total: **62 LOW, 63 MEDIUM, 44 HIGH, 2 UNKNOWN, 0 CRITICAL**. The 44 HIGH findings had no fixed version available in that scan. The gate **passed**; this does **not** mean zero vulnerable packages.
- **Why not blindly gate all HIGH?** If there is no upstream patch, immediate automatic failure may be unactionable. But unfixed findings still need owners, risk assessment, compensating controls and periodic reevaluation; exploitability or exposure may justify blocking anyway.
- **SBOM:** Trivy creates **CycloneDX 1.6**, an inventory of **113 components** at that checkpoint. SBOM ≠ vulnerability scan; it enables future component lookup/incident response. CI uploads the SBOM and full JSON report with **14-day retention**. Current workflow does not itself deploy or enforce required PR branch protection.
- **Decision principle:** **Green CI ≠ no vulnerabilities.** It means the specified policy passed, and it is important to inspect the full report and the gate criteria.

### 4.9 Reproduce / defend it in an AppSec interview

```bash
# On the learning branch, from the repository root with Docker available:
docker build -t expenseguard:local .
docker image inspect expenseguard:local --format '{{.Config.User}}'
# Expected configuration: 10001:10001

# Run locally with the same confinement tested in CI:
docker run --rm -d --name expenseguard-local \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop=ALL --security-opt no-new-privileges=true \
  --pids-limit=100 --memory=256m --cpus=1.0 \
  -p 127.0.0.1:8000:8000 expenseguard:local
curl --fail http://127.0.0.1:8000/health
docker stop expenseguard-local
```

**Five interview responses to practice:**

1. **Image vs container?** Image is the packaged artifact; container is its running instance sharing the host kernel.
2. **Why `python:...-slim-trixie@sha256:...`?** A maintained, relatively small Debian+Python base with a pinned immutable artifact; digest updates remain necessary.
3. **Why requirements before code and multi-stage?** Docker cache reuse and keeping build/dev dependencies out of the final runtime.
4. **Why non-root + read-only + dropped capabilities?** Different least-privilege layers constrain identity, filesystem writes and special kernel privileges after RCE.
5. **Why did a green Trivy job contain 44 HIGH findings?** The full report retained unfixed findings, while our CI gate blocks fixable HIGH/CRITICAL; security policy success is not a vulnerability-free guarantee.

**Milestone boundary:** Docker concepts and the implemented controls above are documented; final SBOM/Trivy interview review is still part of our upcoming lesson. Threat modeling, SSDLC, Terraform, AWS and DAST remain separate workstreams.

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
