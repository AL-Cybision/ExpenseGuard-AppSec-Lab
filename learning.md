# Learning — ExpenseGuard AppSec & DevSecOps

> **Living learning notebook / source of truth for concepts.** Updated: **2026-10-15**. This records what we learned, why it matters, and what is **implemented versus planned**. For onboarding and diagrams, see [README.md](README.md). For the real state of CI, consult the [GitHub Actions runs](https://github.com/AL-Cybision/ExpenseGuard-AppSec-Lab/actions); a green workflow can contain a skipped scanner.
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

### 4.9 SBOM: dependency inventory and supply-chain incident response

**SBOM = Software Bill of Materials.** A machine-readable inventory of software components in a specific artifact, similar to an ingredient list. ExpenseGuard generates a **CycloneDX 1.6** SBOM using Trivy. The verified image contained **113 detected components** in that SBOM. This is a snapshot, **not** continuous monitoring or proof that all software and vulnerabilities were discovered.

| Possible CycloneDX field | Why it matters |
| --- | --- |
| `name` and `version` | Identify component and release for impact assessment. |
| `purl` (Package URL) | Standardize package identity and ecosystem (e.g., PyPI). |
| `hashes` | Identify package artifacts more precisely *when recorded*. |
| `licenses` | Support license reviews *when present*. |
| `dependencies` | Express discovered component relationships *when available*. |

**Illustrative example** (not copied from our generated report):

```json
{
  "type": "library",
  "name": "fastapi",
  "version": "0.142.2",
  "purl": "pkg:pypi/fastapi@0.142.2"
}
```

**Incident scenario:** A critical advisory appears tomorrow for a library. A company has 70 deployed services. Instead of manually opening each repository, its security team searches stored SBOMs for the **affected package and version**, identifies candidate images/services, then checks whether the vulnerable feature is reachable, what privileges it has and which compensating controls or fixes exist. **A match means investigate; it does not automatically prove exploitability.** A non-match only reduces uncertainty if inventory coverage is complete.

**SBOM vs vulnerability scan:** The SBOM answers **what is in the image?** Trivy's vulnerability report answers **which known advisories match these components right now?** Because vulnerability intelligence changes, retain component inventories and rescan/query them when new advisories emerge—even without a code change.

**How to inspect locally** (example commands; not a claim they were executed locally):

```bash
docker build -t expenseguard:local .
trivy image --format cyclonedx --output sbom.cdx.json expenseguard:local
jq -r '.components[] | [.name, .version, .purl] | @tsv' sbom.cdx.json
jq '.components[] | select(.name == "fastapi")' sbom.cdx.json
```

**What we actually implemented:** `.github/workflows/container-security.yml` builds/scans the hardened image, saves `sbom.cdx.json` and `trivy-image.json`, and uploads them as CI artifacts with **14-day retention**. That verifies generation and upload; it is **not a production SBOM registry**, and artifacts are **not yet tied into a deployed-image provenance/inventory service**. Future production work should associate the SBOM with the exact deployed image digest, retain it according to incident-response needs and refresh vulnerability evaluations.

### 4.10 Reproduce / defend it in an AppSec interview

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

**Milestone status (2026-10-08): Docker + Trivy + SBOM fundamentals COMPLETE.** The hardened image, CI runtime smoke test, full Trivy report, fixable HIGH/CRITICAL gate and generated CycloneDX SBOM were implemented and verified at the recorded checkpoint. The SBOM incident-response discussion, limits and interview review are documented here. **This does not mean production-ready:** complete transitive lockfile/hash management, base-image patch cadence, longer-lived SBOM-to-image-digest provenance, triage of unfixed findings, enforced branch protections and ECS production hardening remain future work. Threat modeling, SSDLC, Terraform, AWS and DAST are separate workstreams; **pause before starting them until the user's discussion is complete.**

## 5. AWS IAM — ExpenseGuard mental model, labs and interview guide

> **Status on 2026-10-14:** This is a **learning and design reference**, NOT an implemented AWS deployment. A personal AWS account was created, root MFA was enabled, and a zero-spend budget alert was configured. The account is on a **PAID plan with NO remaining credits**. In the IAM console, we opened the **Policy simulator → Custom mode**; we have NOT yet pasted/simulated the example policy or created any IAM role, S3 bucket, ECS service or RDS database for ExpenseGuard. No billable infrastructure is authorized. A zero-spend budget is **an alert, NOT a spending cap**.

### 5.1 The most important mental model: two identity systems, not one

**Question 1 — Application identity:** Who is the human using ExpenseGuard, and which business objects may they access? A user logs in with email/password; FastAPI validates a session and enforces the ExpenseGuard RBAC/ABAC policy. Example: employee A must not download employee B's receipt (**BOLA/IDOR**).

**Question 2 — AWS identity (IAM):** Which AWS principal is making a request to an AWS service, and is that principal permitted to call this API action on this resource? Example: is the ExpenseGuard **task role** permitted to call `s3:GetObject` on the receipts bucket?

A browser client is **not automatically an AWS IAM user**. In our proposed architecture, employees are app identities and the *backend* assumes/receives an AWS role for infrastructure API calls. An S3 request authenticated by the task role does **not** automatically convey the human's application identity to AWS.

```text
Employee / Manager / App Admin (application identities)
      |
      | HTTPS, ExpenseGuard bearer session
      v
Public ALB -> Private ECS Fargate task: FastAPI
             |  1. AuthN: verify app session
             |  2. AuthZ: authorize user + requested expense/receipt
             |  3. SDK: AWS API request using task-role credentials
             v
        AWS IAM evaluates task-role permissions
             |
             +--> S3: receipt objects
             +--> Secrets Manager: selected application secrets
             |
             +--> RDS PostgreSQL: private network + database authentication
                  (IAM DB authentication is OPTIONAL and not our default assumption)
```

**Two gates for a receipt:** (A) app authorization for the particular employee/object **AND** (B) AWS authorization for the backend role's S3 API action. A role may access the receipts prefix but cannot enforce per-employee business ownership by itself unless we deliberately design a more complex identity-aware delegation model.

### 5.2 Terminology: Who is an IAM principal or identity?

| Term | Useful meaning | ExpenseGuard example |
| --- | --- | --- |
| **AWS account** | Administrative/billing/security boundary that contains AWS resources and IAM configuration | Our paid AWS lab account; not an application user |
| **IAM user** | Long-lived AWS identity, with policies and potentially long-lived credentials | Avoid as application identity and avoid creating permanent access keys |
| **IAM role** | AWS identity with permissions and a **trust policy** that defines who may assume it; normally used through temporary credentials | `ExpenseGuardTaskRole`, `ExpenseGuardDeployRole` |
| **Principal** | An authenticated AWS actor such as an IAM user, assumed-role session, AWS service or federated identity | The assumed ECS task-role session signing an S3 request |
| **STS (Security Token Service)** | AWS service for issuing temporary security credentials / role sessions | ECS task credentials; external CI using OIDC to assume a deployment role |
| **Identity-based policy** | Grants/denies actions and resources to an IAM user/group/role | Role allowed `s3:GetObject` on certain objects |
| **Resource-based policy** | Policy on an AWS resource identifying who may access it (where supported) | S3 bucket policy |
| **Trust policy** | Special resource-based policy on an IAM role deciding who can assume it | ECS tasks service principal |
| **Permission boundary / SCP / session policy** | Other constraints that can limit effective permissions | Advanced controls; not needed for our first simulator exercise |

An **IAM role is not the same as an ExpenseGuard application RBAC role**. Our app roles `employee/manager/admin` concern business rules. AWS IAM roles concern permissions to AWS resources.

### 5.3 Why several AWS roles if the application has many users?

Each independent responsibility should receive **only the permissions it needs**:

| Identity / role | Who uses it? | Expected scope (design only) |
| --- | --- | --- |
| **Workforce administrator** | A person managing the AWS environment | Administrative operations with MFA; do not use account root routinely |
| **ExpenseGuard ECS *task role*** | FastAPI application code running inside an ECS task | Selected S3 receipt objects; selected Secrets Manager reads *if code calls Secrets Manager* |
| **ExpenseGuard ECS *task execution role*** | ECS/Fargate agent/control plane acting to start and support the task | Pull private ECR image, send logs using configured log driver, retrieve secrets referenced by the task definition |
| **GitHub Actions deployment role** | CI after approved security gates | ECR upload and narrowly scoped ECS deployment operations via OIDC/STS; no stored AWS secret access keys |
| **Notification service role** | A hypothetical later worker | Only necessary messaging permissions, not broad S3/infra administration |

**Five ECS replicas ≠ five IAM roles.** Several ECS tasks can reference one task role but receive distinct temporary credential sessions. One task may run multiple containers; they can share the permissions granted to the task role. Split unrelated services/tasks when separate AWS privileges are needed.

**ECS, Fargate, Docker:** Docker/OCI image = packaged FastAPI application; **ECS** = orchestration (task definitions, services, desired count, restart/replacement); **Fargate** = AWS-managed compute/runtime for ECS tasks. Our existing Docker image is a candidate for Fargate but hasn't been deployed. Fargate removes host management, **not** IAM, networking, secrets, app or container-security responsibilities.

### 5.4 Trace a real receipt download request end to end

1. **Employee browser** sends `GET /receipts/123` with an ExpenseGuard bearer session (endpoint hypothetical; **receipt feature not implemented yet**).
2. **FastAPI AuthN** validates the application session and learns which employee is calling.
3. **FastAPI AuthZ** checks owner/department/status and the receipt-to-expense relationship. If employee A requests employee B's receipt, respond **403 before touching S3**.
4. If allowed, **backend code** calls Boto3 `s3.get_object(...)` or generates a narrowly scoped short-lived presigned URL. The AWS SDK automatically finds temporary task-role credentials from ECS's supported credentials provider.
5. **S3 authorizes an AWS API request** using the role/session, action, resource and other applicable policies. The AWS task role is the relevant AWS identity—not the browser user.
6. Backend streams the response or supplies a presigned URL. Treat a presigned URL as a **temporary bearer capability**: anyone who obtains it may use it while valid; only issue it **after** application authorization.

**Interview failure mode:** `s3:GetObject` on the correct bucket **does not fix BOLA**. App authorization must still check *the particular employee and receipt*. Conversely, good app authorization does not grant the backend any S3 permission if IAM denies it.

**RDS nuance:** Connecting to private PostgreSQL requires correct VPC routing/security groups **and** PostgreSQL database authentication (typically username/password stored securely); IAM authentication of the database is a **separate optional configuration**, not implied by a task role. IAM and network security are complementary but different controls.

### 5.5 The fundamental split: TRUST versus PERMISSIONS policy

**Trust policy = WHO may assume a role.** Example illustrative trust policy for an ECS task role (not attached/deployed):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

This only permits a service principal to assume the role under applicable rules; **it does not grant permission to read S3**. In a production configuration, review AWS-recommended restrictions such as `aws:SourceAccount` and `aws:SourceArn` where supported, to narrow the trust relationship.

**Permissions policy = WHAT the assumed identity may do and ON WHICH resources.** Example *identity-based* permissions policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadReceiptObjectsOnly",
    "Effect": "Allow",
    "Action": ["s3:GetObject"],
    "Resource": "arn:aws:s3:::expenseguard-iam-lab-example/receipts/*"
  }]
}
```

**Read the JSON field by field:**

- `Version`: IAM policy language version, **not the application's version**.
- `Statement`: One or more policy rules.
- `Sid`: Optional readable statement identifier.
- `Effect`: `Allow` or `Deny`.
- `Action`: AWS API permission (for example `s3:GetObject`).
- `Resource`: Which ARN (Amazon Resource Name) the rule covers. Here: objects under `receipts/`. This is a **fictional bucket**, not a live resource.
- `Principal`: Often found in resource/trust policies; typically **not** present in an identity-based policy attached to a role.
- `Condition`: Optional conditions such as principal attributes, source context or transport requirements; exact support depends on service/action.

**S3 ARN precision:** `s3:GetObject` applies to **object ARNs**, e.g., `arn:aws:s3:::bucket-name/receipts/*`. `s3:ListBucket` uses a **bucket ARN** (`arn:aws:s3:::bucket-name`) and is **not automatically included** by GetObject. Do not use `"Action":"s3:*","Resource":"*"` just to get a lab working.

### 5.6 The authorization decision: implicit deny, explicit deny, and context

Imagine AWS receives:

```text
Principal: ExpenseGuardTaskRole assumed-role session
Action:    s3:GetObject
Resource:  arn:aws:s3:::expenseguard-iam-lab-example/receipts/123.pdf
Context:   account, request conditions, session, policies, etc.
```

The useful baseline model is:

- **Implicit deny (default):** No applicable policy grants the operation; access is denied. Example: read-only policy has no `s3:DeleteObject` allow.
- **Explicit allow:** A matching permission grants access when all applicable policy types/constraints permit it.
- **Explicit deny:** An applicable `"Effect":"Deny"` overrides an applicable allow.
- **Effective permissions are not just one attached policy.** AWS may evaluate identity policies, S3 bucket/resource policies, session policies, permissions boundaries and organization policies. The exact combination depends on the principal and request context; a resource-based allow can sometimes grant access even without an identity-based allow. **Do not assume that omitting an action in one identity policy guarantees no other policy can grant it.**

In our **isolated custom-policy simulation**, with only the illustrative `s3:GetObject` allow and no other granting policies:

| Simulated request | Expected result | Why |
| --- | --- | --- |
| `s3:GetObject` on `receipts/123.pdf` | **Allowed** | Action and object ARN match |
| `s3:DeleteObject` on `receipts/123.pdf` | **Implicitly denied** | No allow for deletion |
| `s3:GetObject` on `other/123.pdf` | **Implicitly denied** | Resource ARN doesn't match |

**Explicit deny variant** (for learning only): a `Deny` for `s3:DeleteObject` can override a separate `Allow`, but adding more policy rules is unnecessary for our first experiment.

### 5.7 Practical, no-infrastructure IAM Policy Simulator lab — NOT YET EXECUTED

**Account constraints:** AWS **Paid plan**, **$0 credits**; root MFA enabled; zero-spend budget alert enabled. **Never mistake a budget alert for a hard cap.** Avoid S3 buckets, ECS tasks, NAT gateways, ALBs, EC2, RDS, CloudWatch paid features and third-party offerings without a separate cost estimate and explicit approval.

**Progress confirmed from the AWS console screenshots:** IAM → **Policy simulator → Custom**, with a policy named `ExpenseGuard-GetObjectPolicy` selected. It allows `s3:GetObject` only on `arn:aws:s3:::expenseguard-iam-lab-example/receipts/*`. After **Back to simulator**, the console showed **Identity-based policies (1/1)** and **Simulation results (0)**. The Allow/Deny actions have **NOT** been simulated yet.

**Next controlled steps** (perform one at a time, with screenshots/verification):

1. Keep the **already-added and selected** policy in Custom mode and click **Add actions**.
2. Simulate `s3:GetObject` on `arn:aws:s3:::expenseguard-iam-lab-example/receipts/123.pdf` (expected **Allowed**).
3. Simulate `s3:DeleteObject` on the same object (expected **Implicit deny**).
4. Change GetObject to `other/123.pdf` (expected **Implicit deny**, because the prefix differs).
5. Optionally add a second Allow policy limited to `s3:DeleteObject` on `receipts/s7.pdf`; test `s7.pdf` and `123.pdf`. **An Allow only permits an API request; it does not delete an object by itself.**
6. Inspect **Result details**. Record results **only after they actually appear**; review the decision context if unexpected.

**Why Custom mode?** Tests pasted identity-based policies **without creating/attaching a user or role**. This is an IAM **policy simulation**, not a real S3 API call or proof that the same decision will occur in a complex production environment. The console Custom mode cannot fully simulate arbitrary S3 bucket policies or custom organization SCPs; use appropriate advanced tools and real-world verification later. **No real S3 bucket is needed.**

### 5.8 Security review checklist + common misunderstandings

| Misunderstanding | Correction |
| --- | --- |
| "Every ExpenseGuard employee needs an IAM user." | **No.** Ordinary app users authenticate to FastAPI; task role authenticates backend AWS API calls. |
| "IAM knows which human owns receipt 123." | **Not automatically.** Enforce object ownership in app AuthZ before calling S3. |
| "Trust policy lets me read S3." | **No.** Trust decides who assumes a role; permissions decide which AWS actions/resources are allowed. |
| "Task role and execution role are the same." | **No.** App SDK calls use the task role; ECS startup integrations use the execution role. |
| "Role attached means anyone can use it." | **No.** Trust relationship and the applicable assume-role authorization matter; credentials are temporary. |
| "Task role grants PostgreSQL network/database access." | **Not by itself.** Network SG routing and database authentication are different requirements. |
| "A denied action is always explicitly denied." | **No.** Missing matching allow produces **implicit deny**. |
| "S3 prefix scope isolates human users." | **No.** Backend app must check each employee's object permissions. |
| "Policy Simulator guarantees runtime behavior." | **No.** It's a model of policies and context, not a live call with all production constraints. |
| "Our AWS lab can spend credits safely." | **No.** The account is paid and has zero remaining credits. |

**Practical review habits:** Separate people/service/deployment roles; avoid root for daily administration; prefer temporary role credentials over static access keys; minimize actions/resources/conditions; test least privilege with positive and negative cases; check bucket policy and organization constraints; never log raw AWS secrets or app bearer tokens; make IAM + app authorization + network controls complement rather than replace each other.

### 5.9 Existing ExpenseGuard AppSec identity/authentication fundamentals

- **IAM vs application IAM:** AWS IAM manages AWS identities and API permissions. ExpenseGuard's identity model covers users, validated sessions and expense permissions. In both cases **AuthN** establishes an identity and **AuthZ** determines allowed actions.
- **Principal / subject:** Principal is an identity; in ExpenseGuard the **subject** is the principal represented by the current validated session. In AWS an **assumed-role session** is a principal that makes signed API requests.
- **RBAC:** `employee`/`manager`/`admin`. **ABAC:** department, owner, expense status. **DAC/MAC:** other models, not the primary ExpenseGuard policy.
- **PDP / PEP:** Policy Decision Point = computes allow/deny. Policy Enforcement Point = prevents disallowed operations. ExpenseGuard calls `authorize(...)` **before** any expense-status mutation.
- **Least privilege, default deny, separation of duties (SoD):** A manager cannot approve their own expense. **JIT/JEA** are useful access concepts, not implemented ExpenseGuard features.
- **AuthN:** Argon2id password hashes, dummy password verification for missing users, unpredictable opaque bearer tokens, SHA-256 token hashes in server-side sessions, expiry/logout revocation, never `X-User-ID` auth.
- **401 vs 403:** Authentication missing/invalid versus authenticated but forbidden. **BOLA/IDOR:** Changing an expense ID must not expose someone else's record.
- **OWASP API6:** Legitimately allowed workflows abused at scale/sequence (business-flow abuse), distinct from unauthorized-object access (BOLA). Rate limits/business safeguards complement authentication and authorization.
- **Still absent:** Real receipt upload/download, password reset, tenant isolation, MFA enforcement, OAuth/OIDC validation and production persistence. Don't derive future password-reset links from untrusted Host headers.

### 5.10 IAM interview flashcards (answer before reading)

1. **Who is "the identity" when FastAPI calls S3?** Usually the ECS **task-role session**, NOT the logged-in ExpenseGuard employee.
2. **What does ECS Fargate do?** Runs ECS tasks on managed compute; ECS controls task orchestration/desire count; Docker/OCI image packages the app.
3. **Why separate ECS task and execution roles?** Task = business code's AWS APIs (e.g. S3); execution = ECS task startup integration (ECR, logs, task-definition secrets).
4. **Trust policy vs permissions policy?** Trust: who may assume role via STS. Permissions: what API actions/resources that role/session can use.
5. **IAM `s3:GetObject` allowed; employee gets coworker's receipt—root cause?** Application-level BOLA: receipt ownership/authorization wasn't enforced.
6. **Implicit deny vs explicit deny?** No matching permission versus a matching `Deny` statement; explicit deny overrides allow.
7. **One ECS service with five tasks: five roles?** Not necessarily; multiple tasks can share one task-role definition with temporary role sessions.
8. **How do we authenticate to RDS PostgreSQL?** Network access + DB credentials or separately configured IAM DB authentication; task role alone doesn't open database connections.
9. **Why no embedded AWS access key in Docker/GitHub?** Long-lived secrets leak easily; use ECS role temporary credentials or GitHub OIDC role assumption.
10. **What did we actually do in AWS?** Secured account root with MFA, configured alert, navigated simulator to Custom. **Policy Allow/Deny experiment and cloud deployment are NOT yet performed.**

**One-sentence summary for interviews:** "I distinguish application users from AWS principals; ExpenseGuard validates the user's business permission first, then calls AWS through a least-privilege task role with temporary credentials. I separate trust from permissions, execution roles from task roles, and test allow/deny decisions without assuming a green policy simulation proves production security."

**Further reading (AWS official documentation):**
- [AWS IAM policy evaluation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
- [AWS explicit vs implicit deny](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_AccessPolicyLanguage_Interplay.html)
- [AWS IAM JSON policy elements](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies.html)
- [IAM Policy Simulator — Custom mode](https://docs.aws.amazon.com/IAM/latest/UserGuide/policies_policy-simulator-how-to.html)
- [ECS task and execution IAM roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/security-ecs-iam-role-overview.html)
- [ECS task-role credentials](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html)
- [RDS authentication methods](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/database-authentication.html)


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
AWS IAM:   learning notes + architecture model; account MFA/budget configured
Lab next:  IAM Custom policy added; Add actions/Allow-Deny simulation pending
Cloud:     no AWS infrastructure deployed; Paid plan, $0 credits, no cost approval
Later:     Terraform/IaC, AWS implementation, threat modeling/SSDLC artifacts, DAST
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

## 8. AWS Application Security + Terraform — eight-lesson practical workbook

> **Study companion created 2026-10-15:** A separate **21-page PDF** titled *ExpenseGuard AWS Application Security — IAM + Terraform* includes eight detailed lessons, practical steps, policy JSON, Terraform/Checkov examples, security-review cases, drills and evidence worksheets. The PDF was delivered separately, **not uploaded to this repository**. These notes preserve the key concepts and status without requiring old chat transcripts.

**Mandatory cost boundary:** The AWS account is on a **Paid plan with $0 remaining credits**. Root MFA is enabled; a zero-spend budget alert is configured but is **not a spending cap**. Simulated IAM requests, local code/IaC scans and existing read-only account views come first. **No new billable infrastructure or services without a specific cost estimate and explicit approval.** In particular do not create ECS/Fargate tasks, ALBs, RDS, NAT Gateways, S3 objects, ECR repositories, Secrets Manager secrets, CloudWatch log collection, public IPv4 addresses or VPC endpoints during the following simulation/local labs.

### 8.1 IAM fundamentals — actual Policy Simulator exercise (in progress)

- **Request = principal + action + resource + context**. AWS authorizes API operations by evaluating all applicable policy types. No applicable Allow → **implicit deny**; a matching explicit Deny overrides Allow.
- **Current observation:** Custom mode, selected `ExpenseGuard-GetObjectPolicy`, `Simulation results (0)`. The policy editor and selection are verified; Allow/Deny results are NOT verified yet.
- **Lab:** Simulate `s3:GetObject` for fictional `receipts/123.pdf` (expected Allow), then `s3:DeleteObject` (expected implicit Deny), then GetObject for `other/123.pdf` (expected implicit Deny). Inspect matched statements.
- **Extend:** A second Allow policy scoped to `s3:DeleteObject` on `receipts/s7.pdf` would permit that action only for the matching ARN under the isolated simulation. It **does not actually delete s7.pdf**.
- **Security caveat:** Custom Simulator neither executes S3 requests nor fully reproduces arbitrary bucket policies, SCPs, context and running-system authorization. **Never invent observed results.**

### 8.2 STS, role assumption, trust versus permissions, ECS role separation

- **Trust policy = WHO may assume a role**: e.g., `Principal.Service: ecs-tasks.amazonaws.com` with `sts:AssumeRole`; apply AWS-recommended `aws:SourceAccount`/`aws:SourceArn` limits where supported.
- **Permissions policy = WHAT AWS operations that role/session can perform**: e.g., `s3:GetObject` on a private receipt-object prefix. Trusting ECS does not automatically grant S3 access.
- **STS/SDK flow:** ECS provides temporary task-role credentials; Boto3 signs AWS API calls. Avoid permanent AWS keys in Git, environment screenshots or Docker layers.
- **Different roles:** **task role** for FastAPI SDK APIs; **task execution role** for task startup (ECR image pull, configured logs, task-definition secret injection); **CI deployment role** for future GitHub OIDC; separate workforce admin identity.
- **Five ECS task replicas** can share one task-role definition with independent temporary credential sessions. Role count follows privilege boundaries, not employee count.
- **Safe exercise:** Review fictional JSON trust/permissions policies, identify Principal/Action/Resource/Condition, reduce a wildcard and explain why a task execution role does not fix an app SDK S3 AccessDenied.

### 8.3 VPC, public ALB, private ECS and RDS — network trust boundaries

- **Proposed path:** Internet → public ALB HTTPS **443** → private ECS/ExpenseGuard **8000** → private RDS PostgreSQL **5432**.
- **SG rules:** ALB ingress public 443; app ingress 8000 **from ALB SG**; RDS ingress 5432 **from app SG**. Review task public IP setting, route tables, subnet association, egress and NACL return traffic.
- Public subnets have routes to an internet gateway; routability also depends on addresses and SGs. The app's private egress to ECR/S3/secrets may require NAT Gateway or VPC endpoints, potentially **billable**.
- **Safe lab:** Create a DFD/SG table in a local note and classify Internet → ALB, Internet → RDS, ALB → app and app → DB as allowed/denied.
- **Interview:** IAM alone does not allow database TCP connections. Secure DB access needs network boundaries, DB authentication, and TLS.

### 8.4 S3 and Secrets Manager — what IAM does and does not secure

- **Two separate authorization gates for receipts:** FastAPI checks which employee owns or may access the receipt (**BOLA/IDOR prevention**) **before** S3 access. AWS checks that the **backend task-role session** may call GetObject on the object ARN.
- **S3 design:** Block Public Access enabled; scoped identity/bucket policies; private objects; SSE-S3 is enabled by default for new S3 objects; TLS; upload validation; appropriate activity evidence.
- **Presigned URL:** Temporary bearer capability; only issue after business authorization, keep short expiry, protect from log/referrer leakage. An S3 prefix policy alone cannot map a receipt to the correct employee.
- **Secret role nuance:** When ECS task definition references Secrets Manager, task **execution role** often retrieves the secret; when FastAPI code itself calls Secrets Manager, **task role** needs GetSecretValue. Secrets Manager is billable here, so do **not** create secrets.
- **Safe lab:** Review the hypothetical route `subject → receipt lookup → owner check → S3 key → GetObject`. Write negative tests for a non-owner and forged object key. Use simulator only for the IAM half.

### 8.5 ECS Fargate, ECR and task-definition security

- **Docker/OCI image** packages ExpenseGuard; **ECR** stores the image; **ECS** orchestrates tasks and desired replica count; **Fargate** provides managed compute to run them.
- **Review fields:** `taskRoleArn` vs `executionRoleArn`; `awsvpc` networking; private subnet/SG; appropriate CPU/memory; immutable image digest; `readonlyRootFilesystem`; logging; task-health/readiness; runtime secrets.
- Existing **Docker/Trivy/SBOM CI** is implemented; its local `--read-only`/`--cap-drop=ALL`/`--tmpfs`/resource restrictions do **not** automatically deploy into Fargate. Fargate does **not** support privileged containers or `linuxParameters.tmpfs`. Translate supported controls correctly.
- **Safe lab:** Review a static task-definition JSON and find broad task roles, mutable image tags, public reachability, plaintext secrets and unsupported settings. **No ECR image push or ECS task launch.**

### 8.6 CloudTrail, CloudWatch and incident investigation

- **CloudTrail Event history:** AWS management-event history view covering approximately 90 days, region-scoped, available to inspect without configuring a new paid trail. This is not guaranteed coverage of S3 object-level data events.
- **CloudWatch Logs:** Planned for container/application logs; ingest, retention and storage can incur charges, so do not create groups/log streams in our zero-spend lab.
- **Application audit logs:** Future ExpenseGuard must record business actor, action, object, decision and timestamp securely. CloudTrail AWS management events cannot prove which employee's authorization logic allowed a receipt download.
- **Safe lab:** Inspect existing **CloudTrail → Event history** read-only. Examine principal, event name, time, source IP and request context. Don't enable paid data events, Lake, Config or other services.
- **Interview:** Analyze suspicious sts:AssumeRole/IAM policy changes, correlate CI/deploy actions, then investigate actual API data access and business events separately.

### 8.7 Terraform IaC — no-cost local configuration validation

- **Terms:** provider, resource, data source, variable, state, `plan`, `apply`. Terraform code is proposed configuration; `apply` can create **billable AWS resources**.
- **Safe local commands:** `terraform fmt -check -recursive`, `terraform init -backend=false`, `terraform validate`. Init may download plugins. Validate checks syntax/internal consistency; it does not prove security or check live AWS infrastructure.
- **Caveat:** `terraform plan` may contact the AWS provider and require real credentials and state; use only after reviewing the backend/account. **Do not terraform apply.**
- **State security:** never commit `*.tfstate`, `.terraform/` or plaintext credentials. Review `.terraform.lock.hcl` and provider version constraints.
- **Safe lab:** In a local scratch directory define `aws_iam_policy_document` for a restricted receipt GetObject policy; run fmt/validate. This is not provisioning.

### 8.8 Checkov, IaC triage and security gates

- **Local command:** `checkov -d ./terraform --framework terraform` (or scan a dedicated local training folder). Static IaC scanning needs no AWS deployment.
- **Deliberately vulnerable example:** DB SG allowing TCP **5432 from 0.0.0.0/0**. Safer design: private RDS and **only app SG** allowed inbound on 5432.
- **Other review targets:** `Action: "*"` / `Resource: "*"`, broad role trust, public S3, disabled encryption/logging, public RDS, mutable image tags and embedded secrets.
- **Developer finding:** root cause → realistic attack path/preconditions → impacted asset → severity rationale → minimal HCL fix → Checkov rescan → owner and time-limited exception (if warranted).
- **Future pipeline:** Terraform fmt/validate → Checkov → validated review → required PR status check → separately approved deployment. A failing job alone doesn't prove merge protection is enforced.

### Evidence and interview readiness

| Lesson | Evidence to produce before marking practically complete |
| --- | --- |
| IAM | Real screenshot of expected Allowed/Implicit Deny simulation results |
| Roles/STS | Separate trust/permissions policy review; task/execution-role mapping |
| Network | DFD and SG allowed/denied path matrix |
| S3/secrets | BOLA source-to-sink review and presigned URL abuse-case tests |
| ECS | Fargate task-definition static review with runtime compatibility checks |
| Logging | CloudTrail Event history read-only observations |
| Terraform | Local fmt/validate output; no apply |
| Checkov | A real local scan report, secure fix and rescan |

**Interview takeaway:** “ExpenseGuard first authenticates and authorizes the human at the API boundary. Backend code then makes signed AWS calls with narrowly scoped temporary **task-role** credentials; execution-role and deployment-role permissions are separate. Private network design, S3/secret controls, IaC scanning and real testing provide additional defense in depth.”

**Official references:** [IAM evaluation](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html) · [IAM simulator](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html) · [ECS task role](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html) · [Fargate limitations](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html) · [CloudTrail history](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events.html) · [Terraform validate](https://developer.hashicorp.com/terraform/cli/commands/validate) · [Checkov](https://github.com/bridgecrewio/checkov).


## 9. AppSec engineering completion — lessons for resume and portfolio readiness

> **Curriculum prepared 2026-10-15, not all exercises executed.** The companion **19-page PDF**, *ExpenseGuard_AppSec_Completion_Lessons.pdf*, contains seven detailed lessons, local lab commands, insecure/secure examples, templates, evidence matrices and 20 interview questions. It was delivered separately in our chat (not committed to GitHub). **Knowledge-material completion is not implementation verification.** We can now prioritize honest portfolio, resume and interview work while tracking remaining hands-on artifacts as gaps.

### 9.1 Terraform foundation (lesson prepared; lab not verified)

**Goal:** Explain infrastructure as code, provider, resource, data source, state, plan and apply; validate local configuration without creating AWS resources.

- §terraform fmt -check§ checks formatting; §terraform validate§ checks configuration syntax/internal consistency, **not security** or live cloud exposure.
- §terraform init -backend=false§ prepares provider/module requirements for validation without initializing the configured backend. It may still download provider/module code; review dependencies first.
- §terraform plan§ proposes changes and may read AWS/provider state. §terraform apply§ can create billable resources and **requires separately approved cost review**.
- Protect §*.tfstate§, §.terraform/§, sensitive variable files, plan outputs and backend credentials. Review provider pin/§.terraform.lock.hcl§. Keep AWS keys out of code and CI.
- **Safe lab:** Temporary local directory with Terraform's built-in §terraform_data§ resource (no AWS provider); run fmt/init/validate, capture actual stdout. Do not invent a successful execution.

~~~bash
mkdir -p /tmp/expenseguard-terraform-basics
cd /tmp/expenseguard-terraform-basics
# Create a main.tf with terraform_data (see PDF for example)
terraform fmt -check
terraform init -backend=false
terraform validate
~~~

### 9.2 Checkov + AWS misconfiguration review (lesson prepared; lab not verified)

**Goal:** Find and fix unsafe Terraform before deployment. Analyze whether the vulnerable configuration is actually reachable, not merely a scanner label.

- Deliberately unsafe example: PostgreSQL ingress port **5432** from §0.0.0.0/0§; potential exposure depends on routing, IP assignment and other controls.
- Safer principle: private RDS + PostgreSQL ingress **only from the ECS application security group**, encryption, authentication and appropriate egress.
- **Local CLI:** §checkov -d ./terraform --framework terraform§ (point at a deliberately unsafe scratch folder). Checkov static scans do **not** require AWS resources.
- Record Checkov check ID and affected HCL, source/root cause, attack prerequisites, business impact, fix, rescan and regression.
- A §checkov:skip§ annotation is **not** sufficient risk acceptance: require specific exception reason, owner, approver, scope, compensating controls and expiration.

~~~hcl
# Deliberately INSECURE educational SG ingress example; NEVER apply
ingress {
  from_port   = 5432
  to_port     = 5432
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}
~~~

### 9.3 ZAP DAST + FastAPI OpenAPI (lesson prepared; scanner not run)

**Goal:** Inspect the **running** API, save evidence, reproduce findings, and distinguish automatic scanning from authenticated business-logic testing.

- FastAPI exposes §/openapi.json§. ZAP API Scan imports it; the normal API scan uses active testing. §-S§ selects **safe mode**, skipping the active scanner.
- Start with a disposable **local Docker network** and test data. A ZAP container cannot reach the host's §127.0.0.1§ unless networking is deliberately configured; a second container can be reached by name on a shared user-created network.
- **First pass, safe mode:** §zap-api-scan.py -t http://expenseguard-zap:8000/openapi.json -f openapi -S§ using a ZAP image on the same network.
- **Active scan** only after explicit authorization and prepared disposable fixtures, because POST/PUT/DELETE endpoints can mutate state, lock accounts or trigger business flows.
- Authenticated coverage requires a valid session context, role-aware requests and negative assertions. A scanner returning 401 on all protected endpoints does not prove AuthZ safe.
- Test owner vs unrelated employee, cross-department manager, manager's own-expense approval, invalid/expired token and **no mutation after denial**.
- Save actual alerts/request-response evidence; validate manually and retest after remediation. Start ZAP CI as report-only while tuning.

~~~bash
docker network create expenseguard-zap-lab
docker build -t expenseguard:zap .
docker run -d --name expenseguard-zap \
  --network expenseguard-zap-lab expenseguard:zap
docker run --rm --network expenseguard-zap-lab \
  ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py \
  -t http://expenseguard-zap:8000/openapi.json -f openapi -S
~~~

**Security limitation:** API scans are no substitute for server-side object-level ownership checks or source-to-sink analysis.

### 9.4 CI/CD security gates + required PR checks (policy lesson prepared)

**Existing controls:** Pytest/security regression tests, authenticated Semgrep CI, Gitleaks, pip-audit, hardened Docker image/smoke test, Trivy full report + CycloneDX SBOM, Trivy gate on *fixable* HIGH/CRITICAL image vulnerabilities. The Oct 7 Trivy checkpoint reported 171 findings, 44 HIGH with no fixed version. **Passing a gate means the specified policy passed, not zero vulnerabilities.**

**Not verified/implemented:** ZAP scan in CI, Checkov scan in CI, centralized release policy and enforced required branch checks. SonarQube's actual scanner step was previously skipped despite a green workflow.

- Policy starts with **detected → investigated → reproducible → risk-ranked**. CVSS label alone is not a universal shipping decision.
- Candidate gate: confirmed live secrets → block/revoke; validated exploitable SAST → block; reachable critical fixable SCA → block; fixable HIGH/CRITICAL Trivy → existing block; serious verified IaC exposure → block; high-confidence reproducible DAST → block when coverage stable.
- Upstream-unfixed findings require tracking/mitigation or approved exceptions; a green workflow alone must not cause silent acceptance.
- **GitHub branch rules** must require actual checks to stop merges. Distinguish failing job from enforced branch protection. Watch for skipped or path-filtered workflows selected as required checks.
- Enforce least-privilege §GITHUB_TOKEN§, reviewed full-SHA action pins, safe PR trust boundaries, short-lived cloud OIDC credentials and artifact retention.

**Required evidence before claiming operational gate:** Screenshot/record of required checks on target branch, proof the critical check executes on relevant PRs, and proof a failing check actually blocks merging.

### 9.5 Vulnerability management, ownership and exceptions (templates prepared)

~~~text
Alert → deduplicate → validate exploitability → risk-ranked finding
  → assign dev/risk owner & due date → fix or compensate
  → regression test + scan → verify → close with evidence
~~~

Every meaningful finding should provide **description, vulnerable code/config, source-to-sink or attack path, preconditions, impact, severity rationale, root cause, secure alternative, regression tests, verification, and owner/due date**.

**Time-bound exception template:** finding ID, affected asset/digest, exact reason, risk owner, approver, reachability evidence, compensating controls, remediation plan, expiration, review cadence and tracking issue. Do not use an inline scanner suppression as a substitute for approval. Example SLAs (Critical 7 days, High 30, Medium 90, Low 180) are only *illustrative* and must be adopted by an organization before claiming they are policy.

### 9.6 Final AppSec assessment + realistic gap ledger (template prepared)

**What we can demonstrate from existing project:** FastAPI authentication and centralized RBAC/ABAC, regression tests, source/secret/dependency checks, Docker hardening, Trivy, SBOM and documentation.

**What must NOT be implied as already implemented:** PostgreSQL/SQLAlchemy persistence, receipt upload/download, production audit log pipeline, AWS ECS/RDS/S3 deployment, Terraform files, Checkov scan reports, ZAP scan reports, enforced release PR checks, and a signed full AppSec assessment.

**Assessment outline:** scope + tested commit/date → architecture/assets/trust boundaries → methodology and excluded surfaces → verified findings (severity rationale/evidence) → fixes/regressions → controls matrix → residual risks → prioritized backlog → sign-off/review owners.

**Portfolio evidence packet:** 1 architecture diagram labeled *current vs planned*; 2-3 sanitized reproducible findings with secure patches and negative regression tests; CI job evidence including skipped steps; Trivy/SBOM artifacts; IAM design/trust-vs-permission explanation; developer checklist; accurate open gaps.

### 9.7 Developer enablement, PR checklist and interview defense (templates prepared)

**One-page secure coding principles:** derive user identity from verified session, authorize every object/action before side effects, deny by default, prevent same-user expense approval, handle files and S3 object keys safely, avoid logging secrets/tokens/presigned URLs, use prepared DB operations, isolate runtime credentials, minimize dependencies and write positive/negative tests.

**PR checklist:**
- [ ] Entry points, assets and trust boundaries identified
- [ ] AuthN/ownership/role/department checks occur *before* data access/mutation
- [ ] Negative regression tests prove no side effects after denied access
- [ ] File upload, validation, sessions, errors and logging reviewed where relevant
- [ ] Secrets, dependencies, images, Terraform/CI changes reviewed
- [ ] Scanner findings triaged; exceptions have risk owner/expiry
- [ ] Required CI steps actually executed; skipped scans are visible

**Release checklist:** commit/tag/image digest; required branch checks; fix/accepted risk ledger; reviewed secrets/IAM/SG; tested rollback and logging; approved cloud costs. A container SBOM is not a vulnerability scan; an IAM Allow is not app-level BOLA protection.

**Interview questions to rehearse:**
1. Why isn't §terraform validate§ a cloud security scan?
2. What is the difference between Checkov policy violations and exploitability?
3. How does ZAP import the FastAPI OpenAPI specification, and why start passive?
4. Why can't unauthenticated DAST establish BOLA resistance?
5. How do you separate a CI security gate from branch-rule enforcement?
6. Why can an image with 44 HIGH findings pass a fixable-only Trivy gate?
7. How do you defend a justified, expiring risk acceptance?
8. How do you get a developer to implement the **root-cause fix**, not merely suppress a finding?
9. What can be claimed as *implemented and verified* in ExpenseGuard today?
10. Which security evidence remains open before claiming production-ready deployment?

### 9.8 Transition decision and honest learning-completion status

**Learning curriculum:** AWS study guide (created separately) + the seven remaining AppSec lessons above **prepared**. We may transition to **resume, portfolio and interviews immediately**, practicing these concepts through interview questions and code reviews.

**Not the same as practical certification:** No Terraform/Checkov/ZAP executions or AWS deployment were performed just by generating this PDF. Treat those as explicit evidence gaps; do **not** fabricate scans, tests, findings or production experience in a CV.

**References:** [Terraform validate](https://developer.hashicorp.com/terraform/cli/commands/validate) · [Checkov CLI](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html) · [ZAP API Scan](https://www.zaproxy.org/docs/docker/api-scan/) · [ZAP Docker networking](https://www.zaproxy.org/docs/docker/about/) · [GitHub required rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets) · [OWASP WSTG](https://owasp.org/www-project-web-security-testing-guide/).

**Notebook convention:** Append short, verified lessons after each milestone. Label **implemented**, **tested**, and **planned** honestly; revise dated status claims rather than presenting them as permanent truths.
