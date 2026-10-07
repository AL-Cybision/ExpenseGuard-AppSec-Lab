# ExpenseGuard — Application Security Engineering Lab

**Learn how a small business API is built, tested, secured, and eventually prepared for cloud deployment.**

ExpenseGuard is a hands-on **Application Security (AppSec) / DevSecOps** portfolio project. It models employee expense reimbursement: an employee asks their employer to repay an eligible work expense, and an authorized manager reviews that request. The goal is not to build a commercial expense product. It is to show *why* security controls exist, *where* they belong, *how* they can fail, and *how* engineers test them.

> **Project maturity:** Working Python/FastAPI learning application with in-memory data and automated tests; security checks run in GitHub Actions. A hardened Docker image, Trivy image scanning and CycloneDX SBOM generation are now implemented in CI. **This is still not a production service and is not deployed to AWS.** The architecture and cloud sections below distinguish current functionality from planned work.

## Start here: the project in 60 seconds

| Question | Answer |
| --- | --- |
| What does it do? | Employees create and submit expense reimbursement requests; managers approve or reject requests within their department. |
| What does it teach? | Authentication, authorization, secure code review, security testing, vulnerability triage, CI/CD security, and eventually containers/cloud security. |
| What is running today? | A local **FastAPI REST API**, Python business/security logic, demo users/expenses, a test suite, and a hardened Docker image that is built/tested in CI. |
| Where is the data? | **Python dictionaries in process memory**. Restarting the server loses new data/sessions; there is **no database yet**. |
| Can I log in? | Yes: a demo login issues an opaque bearer session token; the old `X-User-ID` learning stub **does not authenticate** users. |
| Does GitHub deploy it? | **No.** GitHub Actions now test source code and build/scan the Docker image, but there is **no deployment job** yet. |
| Is AWS live? | **No.** The AWS diagram is a target design, not existing infrastructure. |

### A simple business example

Noman works in Engineering. He pays **PKR 2,500** for transport to a client meeting. He creates an expense request and submits it. A manager in Engineering may review it, but a manager in Finance may not approve it; a manager also may not approve their own expense. Those rules are enforced on the server, not trusted to a browser or an HTTP header.

An expense moves through this simplified lifecycle:

~~~mermaid
flowchart LR
    A[Draft: created] -->|Owner submits| B[Submitted: awaiting review]
    B -->|Authorized manager approves| C[Approved]
    B -->|Authorized manager rejects| D[Rejected]
~~~

**Implemented operations:** create, read, submit, approve and reject expenses. Editing draft details, payment processing, receipts, registration and password reset are not implemented yet.

## 1. Two useful terms: AppSec and DevSecOps

- **Application Security (AppSec):** designing, reviewing and testing software so people can use it without gaining unauthorized access or abusing its functions.
- **CI (continuous integration):** automatic checks whenever code is pushed or proposed in a pull request (PR). A PR is a request to review and merge code.
- **CD (continuous delivery/deployment):** preparing or releasing tested software automatically. **ExpenseGuard currently has CI checks, not a deployment pipeline.**
- **DevSecOps:** making security checks part of the ordinary engineering workflow, alongside code changes and tests, instead of postponing security until release.

The point of this project is not just "install Semgrep." It is to **detect → understand → validate → remediate → regression-test → re-scan** a problem.

## 2. How the application works today (implemented)

~~~mermaid
flowchart TD
    Client["Client: curl / browser / API tool"]
    API["FastAPI routes\napp/main.py"]
    AuthN["Authentication\napp/authentication.py\nverify password / validate session"]
    Policy["Authorization\napp/authorization.py\nallow or deny action"]
    Data[("In-memory demo accounts,\nsessions, users, expenses\napp/data.py")]
    Client -->|"HTTP + Authorization: Bearer token"| API
    API --> AuthN
    AuthN <--> Data
    AuthN -->|"Validated Subject"| Policy
    Policy <--> Data
    Policy -->|"Allowed?"| API
    API -->|"HTTP response"| Client
~~~

**REST API** means a service that accepts HTTP requests such as `GET /expenses/102` and returns data, usually JSON. **FastAPI** routes those requests to Python functions. **Pydantic** validates request/response structures. **Uvicorn** runs the web server.

### Authentication: *Who are you?*

1. The client sends an email and password to `POST /auth/login`.
2. The server normalizes the email and checks the submitted password against a stored **Argon2id password hash**. A hash is a one-way representation; the database should not store plaintext passwords. An unrelated dummy Argon2 verification is performed for nonexistent accounts to reduce simple timing differences.
3. A successful login creates an unpredictable **opaque token**, returns its raw value to the client once, and stores only a **SHA-256 hash** of that token in the in-memory session store.
4. Later requests supply `Authorization: Bearer <token>`. The API hashes the supplied token, finds the session, checks expiry/revocation and whether the account remains active, then constructs the authenticated identity.
5. `POST /auth/logout` revokes that session. Sessions have an eight-hour absolute lifetime.

The **raw token is a secret**: anyone holding it can act as its user until it expires or is revoked. Treat it like a password; never put it in a public issue, repository, or log.

### Authorization: *What may you do?*

Authentication alone does not grant every permission. A separate `authorize(subject, action, expense)` function decides whether a verified user can perform an operation on a particular expense.

This combines **RBAC** (role-based access control: employee, manager, admin) with **ABAC-style conditions** (attributes such as owner, department and expense status).

| Operation | Server-side rule |
| --- | --- |
| Read | Owner may read; manager may read within own department; admin may read all. |
| Create | Valid authenticated user creates an expense owned by their verified identity. |
| Submit | Only the owner, and only while the expense is `draft`. |
| Approve or reject | Only a manager in that expense's department, only when `submitted`, and **never their own expense**. |
| Anything else | **Deny by default** unless an explicit rule allows it. |

For example: **changing an expense ID** must not let an employee view someone else's expenses (a broken object-level authorization / IDOR-style scenario). Approval is checked **before** the expense's status changes; this prevents an unauthorized request from changing data even if it eventually returns HTTP 403.

**Trust boundary:** Client-supplied headers, expense IDs and JSON are untrusted. The API must derive the user from the validated server-side session, then independently check permission against the requested object.

## 3. Technology choices and why they matter

| Technology / file | Job in this project | Why it was selected |
| --- | --- | --- |
| **Python** | Application and test language | Readable, widely used for APIs and security tooling. |
| **FastAPI** | HTTP routes and automatic OpenAPI docs | Makes API behavior easy to inspect and test. |
| **Pydantic** | Input/output models | Applies type and field constraints at API boundaries. |
| **Uvicorn** | Local application server | Runs the FastAPI app locally. |
| **Argon2id / argon2-cffi** | Password hashing | Purpose-built, configurable password hashing rather than fast general-purpose hashes. |
| **`secrets` + SHA-256** | Issue unpredictable bearer tokens; store token hashes | Limits exposure from accidental disclosure of the session store. SHA-256 is used for **high-entropy tokens**, not instead of Argon2id for passwords. |
| **Python dataclasses / dictionaries** | Demo accounts, sessions and expenses | Keeps the first identity/authorization lessons small and inspectable; deliberately not durable storage. |
| **Pytest + HTTPX** | Unit and HTTP/API regression tests | Proves intended behavior and that known authorization bugs stay fixed. |
| **Git + GitHub** | Version control and code review | Records changes and supports PR-oriented development. |
| **GitHub Actions** | Automated CI jobs | Runs repeatable checks on pushes and PRs. |
| **Gitleaks** | Secret scanning | Checks for accidentally committed credentials. |
| **Semgrep** | Static analysis (SAST) | Flags risky source/configuration patterns for human validation. |
| **pip-audit** | Python dependency analysis (SCA) | Checks dependency versions against known advisories. |
| **Dependabot** | Dependency/action update proposals | Helps keep dependencies current through reviewable PRs. |
| **SonarQube Cloud** | Additional analysis and coverage dashboard | Configured as an optional integration; **actual scans are not yet active**. |
| **Docker** | Packages the API and runtime dependencies | Makes the deployable artifact explicit and repeatable; the default image runs as non-root. |
| **Trivy** | Scans the built image for known OS/Python vulnerabilities | Checks the artifact that would actually be shipped, not only source dependencies. |
| **CycloneDX SBOM** | Inventories packages/components inside the image | Gives a machine-readable component list for later vulnerability and incident response. |

**Planned, not yet implemented:** PostgreSQL + SQLAlchemy/Alembic (persistent database and migrations), Checkov (Terraform/IaC scanning), OWASP ZAP (dynamic testing), Terraform and AWS services.

## 4. Run ExpenseGuard locally

**You need:** Git, Python 3.11 or newer, a terminal, and internet access to install Python packages. CI currently uses **Python 3.12**; local testing also ran under Python 3.14 with non-fatal deprecation warnings.

The latest functionality is on the learning branch, **not yet merged into `main`**:

~~~bash
git clone https://github.com/AL-Cybision/ExpenseGuard-AppSec-Lab.git
cd ExpenseGuard-AppSec-Lab
git switch --track origin/learning/authentication-fundamentals

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
uvicorn app.main:app --reload
~~~

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

Open **http://127.0.0.1:8000/docs** for interactive API documentation, or **http://127.0.0.1:8000/health** for `{"status":"ok"}`. `--reload` is **for local development only**.

### Try the API (safe demo data)

The repository includes development-only demo identities. For the seeded Noman account, a test-only credential is documented in `tests/test_authentication.py`. **Never reuse demo credentials or store real user passwords in a public repository.**

~~~bash
# In another terminal, while the server is running:
curl -s http://127.0.0.1:8000/health

# Log in with the TEST-ONLY Noman demo password.
# Python extracts the bearer token from the JSON response.
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"noman@example.com","password":"Noman Demo Password 2026"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# Identify the logged-in user:
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/whoami

# Owner is allowed to read expense 102:
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/expenses/102

# Owner is NOT allowed to read another person's expense 103 (expect 403):
curl -i -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/expenses/103

# End this session:
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/auth/logout
unset TOKEN
~~~

**HTTP status guide:** `200` means the request succeeded; `201` means a resource was created; `401` means the caller is not successfully authenticated; `403` means an authenticated caller lacks permission; `404` means a resource was not found.

The original lab used `X-User-ID` as a teaching shortcut. **That header no longer authenticates users.** The request must contain a valid bearer token.

### Available endpoints

| HTTP method + path | Purpose |
| --- | --- |
| `GET /health` | Health check (no login required). |
| `POST /auth/login` | Obtain session token with demo email/password. |
| `POST /auth/logout` | Revoke current bearer session. |
| `GET /whoami` | Describe identity derived from session. |
| `POST /expenses` | Create draft expense for authenticated user. |
| `GET /expenses/{expense_id}` | Read an authorized expense. |
| `POST /expenses/{expense_id}/submit` | Submit owned draft. |
| `POST /expenses/{expense_id}/approve` | Approve submitted expense if allowed. |
| `POST /expenses/{expense_id}/reject` | Reject submitted expense if allowed. |

## 5. What happens when code is pushed? The CI/CD security pipeline

A developer changes code, commits it, and opens a **pull request** to propose a change. **GitHub Actions** reads YAML workflows in `.github/workflows/` and runs automated checks.

**Important implementation detail:** In this repository, the checks are **separate workflows triggered in parallel**, not one linear release pipeline. Source-security workflows run broadly; the container workflow is path-filtered to application/container changes. CI now **builds and scans** a Docker image, but it does **not deploy** the application or enforce a centralized release policy yet.

~~~mermaid
flowchart TD
    PR["Push / pull request / manual run"] --> GHA["GitHub Actions: independent checks"]
    GHA --> TEST["Pytest\nfunctional + security regression tests"]
    GHA --> SECRET["Gitleaks\naccidental credential detection"]
    GHA --> SAST["Semgrep\nsource/configuration analysis"]
    GHA --> SCA["pip-audit\nknown dependency vulnerabilities"]
    GHA --> SONAR["Coverage + SonarQube integration\nscanner currently skipped"]
    TEST --> REVIEW["Review workflow results"]
    SECRET --> REVIEW
    SAST --> REVIEW
    SCA --> REVIEW
    SONAR --> REVIEW
    REVIEW --> DECISION["Human remediation / review\nbefore any release"]
~~~

### Each control answers a different question

| Check | Plain-language security question | Workflow | Current behavior |
| --- | --- | --- | --- |
| **Unit and security regression tests** | Did a change break application behavior or reintroduce forbidden actions? | `python-tests.yml` | Runs Pytest; **36 tests passed** on the Oct 3 checkpoint. |
| **Secret scanning** | Did an API key, password or token accidentally enter Git? | `secret-scan.yml` | Gitleaks scans full Git history; latest job passed. A successful job is **not proof every secret is absent**. |
| **SAST** (static application security testing) | Does code or configuration contain risky patterns? | `semgrep.yml` | Authenticated `semgrep ci` is operational; the verified Oct 3 run completed successfully and reported 0 findings for that revision. |
| **SCA** (software composition analysis) | Are imported third-party packages affected by known advisories? | `sca.yml` | `pip-audit` runs against `requirements.txt`; latest job reported **no known vulnerabilities** after dependency upgrades. |
| **Coverage and code-quality analysis** | Which application code was tested, and what other problems can static analysis identify? | `sonarqube.yml` | Coverage test step passed; **SonarQube's scanning step was skipped** without required credentials/project variables. |
| **Dependency maintenance** | Who helps propose updates to Python packages and CI Actions? | `.github/dependabot.yml` | Weekly update checks, 5-PR limits, and explicit 7-day cooldown for routine updates. |
| **Container build + scan + SBOM** | Is the deployable image hardened, runnable and affected by known package vulnerabilities, and what exactly is inside it? | `container-security.yml` | Builds the digest-pinned, non-root image; smoke-tests it with read-only filesystem/capability restrictions; runs Trivy; uploads a CycloneDX SBOM and JSON scan report; gates fixable HIGH/CRITICAL findings. |

**A scanner alert is evidence to investigate, not automatic proof of exploitability.** For example, the Semgrep review found mutable GitHub Action tags, Dependabot configuration recommendations, and an affected development dependency. We analyzed the root causes rather than calling every alert a remote API vulnerability.

### Implemented CI hardening and design decisions

- **Least-privilege workflow token:** workflows declare `permissions: contents: read` rather than granting broad write permissions by default.
- **Immutable Action references:** third-party `uses:` references are pinned to full commit SHA values, instead of mutable labels such as `@v6`. These references must still be reviewed when upgraded.
- **Explicit tool versions:** important scan tools are version-pinned for repeatability; direct Python dependencies have fixed versions in `requirements.txt`. A fully locked transitive dependency graph and reproducible image builds are future improvements.
- **Timeouts:** jobs have time limits so a stuck process does not run indefinitely.
- **Concurrency control:** superseded runs on the same ref can be cancelled, reducing redundant jobs.
- **Supply-chain caution:** Dependabot's cooldown avoids immediately proposing every newly released version; dependency security updates still require prompt review.
- **Fail visibly:** `pip-audit` can fail the job on a reported vulnerability. A failed scanner is **not automatically the same thing as a blocked merge**; branch-protection/required-check settings must be verified separately.
- **Separation of duties:** developers should not simply suppress a finding to make a dashboard green. A reviewer should evaluate the risk and verify the evidence.

### What CI needs before we can call it complete

1. Configure SonarQube Cloud's `SONAR_TOKEN` secret and `SONAR_PROJECT_KEY` / `SONAR_ORGANIZATION` variables if we choose to enable that integration; confirm the scanning step really executes and inspect its quality gate.
2. Prove secret-scanning behavior with a **harmless synthetic test string**, not live credentials; remove test artifacts safely.
3. Decide and document broader **severity-based security gates**, required PR checks, false-positive triage, justified exceptions, owners and expiration dates.
4. Add infrastructure/IaC and dynamic checks as Terraform and a staging environment become available.

### Configuration: secrets stay out of source code

GitHub → repository **Settings → Secrets and variables → Actions** is where CI credentials belong. **Never paste values into the README, YAML, screenshots or issues.**

| Setting | Type | Purpose |
| --- | --- | --- |
| `SEMGREP_APP_TOKEN` | Secret | Allows GitHub Actions' `semgrep ci` to send authenticated scan results to Semgrep AppSec Platform. |
| `SONAR_TOKEN` | Secret | Authorizes a SonarQube Cloud scan. |
| `SONAR_PROJECT_KEY` | Repository variable | Selects the SonarQube project. |
| `SONAR_ORGANIZATION` | Repository variable | Selects the SonarQube organization. |
| `GITHUB_TOKEN` | GitHub-provided token | Used by Gitleaks workflow; repository permissions remain limited. |

A production cloud deployment should use **GitHub OIDC (short-lived credentials)** to assume an appropriately restricted AWS role; no long-lived AWS access keys should be placed into CI.

## 6. Findings, remediation and evidence

The engineering standard for meaningful findings is:

~~~text
Detection
  → Inspect the exact rule/advisory and affected file/version
  → Determine attacker influence, reachability and environment
  → Decide: true positive, false positive, or needs more context
  → Explain root cause and realistic impact
  → Make the smallest secure change
  → Add/adjust regression tests
  → Re-run scans and confirm closure
  → Document remaining risks and communicate with developers
~~~

One real example in this lab: `pytest==8.4.1` and older Starlette dependencies triggered security advisories. We reviewed compatibility, upgraded to `pytest==9.0.3`, `fastapi==0.142.2` and `starlette==1.6.0`, and reran checks. On **2026-10-03**, GitHub Actions reported **36 passing tests** and `pip-audit` reported **no known vulnerabilities** against the pinned requirements. This statement is limited to that scan at that time; it is not a claim of zero application risk.

**Exception policy (planned):** If a finding cannot be fixed immediately, document its identifier, impact, environment, compensating controls, owner, approver, expiry date and re-review date. A suppression or ignored alert is not an automatic risk acceptance.

## 7. Container security: Docker + Trivy (implemented)

A **container image** packages the operating-system userspace, language runtime, dependencies and application code. ExpenseGuard keeps an intentionally weak `Dockerfile.insecure` for comparison, while the default `Dockerfile` is the hardened build path.

The hardened image currently uses a Python 3.12.15 slim base **pinned by digest**, a multi-stage build, a dedicated UID/GID 10001, runtime-only Python dependencies, `.dockerignore`, a health check and no application secrets copied into the image. CI smoke-tests the container using `--read-only`, a small temporary filesystem, `--cap-drop=ALL`, `no-new-privileges`, PID/memory/CPU limits, then runs Trivy.

Verified on **2026-10-07** at commit `cfbcc70`:
- image build, non-root check and hardened smoke test: **passed**;
- Trivy full report: **171 findings** (62 LOW, 63 MEDIUM, 44 HIGH, 2 UNKNOWN, 0 CRITICAL);
- all 44 HIGH findings in that scan had **no fixed version**, so the current gate—**block fixable HIGH/CRITICAL findings**—passed;
- CycloneDX **1.6** SBOM generated with **113 components** and uploaded with the JSON Trivy report as a 14-day GitHub Actions artifact.

This is intentionally a nuanced result: **a green container job does not mean zero vulnerabilities**. The full report remains evidence for triage; the gate represents an explicit release policy, not a claim that unfixed upstream CVEs do not matter.

## 8. Planned cloud architecture (AWS): **not deployed**

**Cloud** means renting computing and managed services instead of owning the physical servers. AWS is our learning target, chosen because it exposes realistic application, network, data, identity and logging controls. We will review Terraform and costs **before creating paid infrastructure**.

~~~mermaid
flowchart TD
    User["Internet users"] --> ALB["Public Application Load Balancer\nTLS / request routing"]
    subgraph VPC["AWS VPC: isolated network"]
        ALB --> ECS["ECS Fargate\nprivate containerized FastAPI service"]
        ECS --> RDS[("Private RDS PostgreSQL\nauthoritative application data")]
        ECS --> S3[("Private S3 bucket\nreceipt files")]
        ECS --> SEC["AWS Secrets Manager\napplication secrets"]
    end
    ECR["Amazon ECR\ncontainer image registry"] -.-> ECS
    IAM["AWS IAM\nleast-privilege identities / roles"] -.-> ECS
    ECS --> CW["CloudWatch\napplication/operations logs"]
    AWS["AWS account activity"] --> CT["CloudTrail\naudit of AWS API operations"]
    GIT["GitHub Actions: future deployment workflow"] -.->|"OIDC temporary role, after approved gates"| IAM
~~~

### AWS services in everyday language

| AWS / tool | What it does | Security decision we will test |
| --- | --- | --- |
| **VPC, public/private subnets** | Network boundary and network segments | Expose only the load balancer; keep application tasks and database private where possible. |
| **ALB (Application Load Balancer)** | Public front door that routes web requests | TLS, controlled ingress and health checks. |
| **ECS Fargate** | Runs container workloads without managing virtual machines directly | Restricted runtime permissions, network access and image source. |
| **ECR** | Stores container images | Only trusted images; access control and scanning. |
| **RDS PostgreSQL** | Managed relational database | Private connectivity, backups, encryption and restrictive security groups. |
| **S3** | Object storage for receipts | Block public access, encrypt objects, authorize file access, carefully scope presigned URLs. |
| **IAM** | AWS identity and permission system | Different roles for deployment and application; no wildcard permissions without justification. |
| **Secrets Manager** | Secure service for application credentials | Retrieve through roles at runtime rather than embedding secrets in Git or images. |
| **CloudWatch** | Logs and operational monitoring | Useful audit signals without tokens, passwords or unnecessary sensitive details. |
| **CloudTrail** | Audit trail of AWS API activities | Investigate changes to cloud infrastructure and identity permissions. |
| **Terraform** | Infrastructure as Code (IaC): cloud resources described in files | Review IaC for public exposure, risky IAM, missing encryption, unsafe configuration and drift. |
| **Checkov / Trivy IaC** | Scans Terraform before deployment | Catch misconfigurations before resources are created. |

The intended data flow is **Internet → ALB → ECS Fargate → FastAPI → private RDS**, with separate controlled access to S3 and secrets. We will first run `terraform fmt`, `terraform validate`, `terraform plan` and an IaC scan. **Do not run `terraform apply` or launch chargeable AWS services without explicit approval and a cost estimate.**

### Why ECS first, not Kubernetes?

Kubernetes is useful for securing complex cluster-based environments, but it introduces significant operational scope. The primary project targets **AppSec, CI/CD, IAM and cloud architecture**, so ECS Fargate is the planned main deployment. A small local Kubernetes **kind/k3d** workload-security exercise can follow as a stretch project; it is **not** a current feature.

## 9. The eventual full DevSecOps pipeline

The following is a **target design**, not a diagram of already configured workflows:

~~~mermaid
flowchart TD
    PR["Developer pull request"] --> UT["Unit + authorization/security tests"]
    PR --> SE["Secret scanning"]
    PR --> SA["SAST"]
    PR --> SC["SCA"]
    UT --> BUILD["Docker image build"]
    SE --> BUILD
    SA --> BUILD
    SC --> BUILD
    BUILD --> IMG["Trivy image scan"]
    BUILD --> BOM["SBOM inventory"]
    PR --> IAC["Terraform IaC scan"]
    IMG --> RISK["Documented security/risk policy"]
    BOM --> RISK
    IAC --> RISK
    RISK -->|Pass| STAGE["Isolated staging environment"]
    RISK -->|Blocking finding| FIX["Fix / retest"]
    RISK -->|Approved time-limited exception| STAGE
    STAGE --> ZAP["ZAP DAST against running staging API"]
    ZAP --> RELEASE["Separate release approval / deployment"]
~~~

- **SAST** analyzes code without needing the API running.
- **SCA** checks imported libraries for known vulnerabilities.
- **Secret scanning** looks for committed credentials.
- **Container scanning** checks the built image, including system packages.
- **IaC scanning** checks cloud definitions such as Terraform.
- **SBOM** (software bill of materials) inventories software components; it does not fix vulnerabilities.
- **DAST** (dynamic application security testing) exercises the **running** API; OWASP ZAP is the planned tool.
- **Severity gates** decide which validated findings block a change. Real policies should account for reachability, business impact and context, not just a scanner's label.
- **Risk acceptance** is a documented, approved, time-limited exception rather than silently disabling checks.
- **Release/deployment** is separate from running a source-code scan: no automatic deployment exists today.

## 10. Planned AppSec learning milestones

| Workstream | Evidence we want |
| --- | --- |
| **Current: finish CI/CD security** | Authenticated Semgrep CI, dependency and secret checks, validated findings, Action SHA pinning, reviewed policies. |
| **Application hardening** | Secure password reset, rate-limiting approach, security logging, secure file upload/download and tests. |
| **Tenant isolation / OAuth & OIDC** | Organization membership model, cross-tenant access tests, validated tokens/scopes/audiences and clear trust boundaries. |
| **Threat modeling and SSDLC** | Data-flow diagrams, STRIDE threats, abuse cases, security requirements, release/PR checklists and risk register. |
| **Docker / Trivy / SBOM** | Insecure vs hardened image, image-scan comparisons and component inventory. |
| **Terraform / AWS** | Reviewable VPC/ECS/RDS/S3/IAM configuration, IaC findings, least-privilege roles, logs and cost-aware plan. |
| **DAST and gates** | Authenticated staging tests where possible, severity and exception process, evidence from CI. |
| **Optional AI Product Security** | Expense policy assistant with authorization-aware retrieval, indirect prompt-injection and cross-tenant leakage tests. |
| **Portfolio assessment** | Findings, fixes, regression tests, architecture decisions, security review and interview-ready explanations. |

## 11. Known limitations and honest security boundaries

This repository is **an educational security lab**, not a ready-to-run enterprise expense system. Today it has:

- Demo identities and seeded test data; **no registration, password reset, MFA enforcement, persistent database or real finance processing**.
- In-memory sessions and data that do not survive a restart or scale across servers.
- No production-grade rate limiting, account recovery workflow, production identity provider or comprehensive audit pipeline yet.
- No receipt upload/storage, tenant separation, TLS termination configuration, production hosting or AWS infrastructure yet.
- Docker/Trivy/SBOM are implemented, but Checkov/IaC and ZAP/DAST are not yet integrated; branch-protection/release gates are not yet verified.
- Authenticated Semgrep CI is operational; SonarQube's actual analysis step is still not operational on the latest reviewed run.

**Security depends on configuration and ongoing review:** even green automated checks cannot prove a system is free of vulnerabilities. The objective is to make concrete, repeatable security evidence and to document tradeoffs and fixes transparently.

## 12. Repository guide

~~~text
app/
  main.py             HTTP API, request models, session dependencies, routes
  authentication.py   Argon2id password and bearer-token helpers
  authorization.py    Centralized allow/deny authorization policy
  models.py           Identity, session, expense and policy data models
  data.py             In-memory learning data and demo accounts

tests/
  test_authentication.py   Password, login, tokens, expiry, logout tests
  test_authorization.py    Authorization policy rules
  test_api.py              End-to-end API permission behavior
  conftest.py              Test data fixture

.github/
  workflows/
    python-tests.yml       Pytest regression checks
    secret-scan.yml        Gitleaks secret scanning
    semgrep.yml            Semgrep AppSec Platform CI
    sca.yml                pip-audit dependency scanning
    sonarqube.yml          Coverage and conditional SonarQube analysis
    container-security.yml Docker build, hardened smoke test, Trivy and SBOM
  dependabot.yml           Package / Action update policy

requirements-runtime.txt   Runtime-only Python dependencies for container
requirements.txt           Development/test dependencies + runtime include
Dockerfile                 Hardened default container image
Dockerfile.insecure        Educational anti-pattern comparison
.dockerignore              Removes unnecessary/sensitive build-context files
sonar-project.properties   SonarQube analysis settings
README.md                  This guide
~~~

## 13. How to evaluate the work (or contribute)

If you are new to security, start by running the application and reproducing **one allowed request** and **one 403 denial**. Next read `app/authorization.py` and the tests to understand *why* the decision differs. Finally inspect the **Actions** tab to see how continuous checks work.

For each proposed security change, try to record: **what could go wrong → how to reproduce or detect it → root cause → safe fix → regression test → evidence that the fix works**. Please use test credentials only, never target third-party systems without authorization, and never commit real secrets.

**Project owner:** [AL-Cybision](https://github.com/AL-Cybision)  
**Reference curriculum:** [jassics/security-study-plan](https://github.com/jassics/security-study-plan)

---

*This README intentionally labels planned systems as planned. It will evolve as ExpenseGuard gains AWS, Terraform, DAST and broader security-gate implementations.*
