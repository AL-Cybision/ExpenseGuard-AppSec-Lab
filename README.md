# ExpenseGuard IAM Lab

ExpenseGuard is a small **employee expense reimbursement application** built to learn IAM and Application Security.

## Business purpose

Employees sometimes spend their own money for legitimate company work, for example:

- travel to a client meeting;
- a work-related software subscription;
- an approved team meal;
- office or project supplies.

They create an **expense reimbursement request** asking the company to repay them.

There are no customer orders in this lab.

## Workflow

1. `draft` — the employee created the expense and may still edit it.
2. `submitted` — the employee sends it to a manager for review.
3. `approved` — the manager accepts it for reimbursement.
4. `rejected` — the manager refuses it.

Example:

> Noman paid PKR 2,500 for a taxi to a client meeting. He creates a draft expense, attaches evidence later, and submits it. A manager in his department reviews and approves or rejects it.

## Current IAM rules

- Employees may read their own expenses.
- Managers may read expenses in their department.
- Administrators may read every expense.
- Only the owner may submit an expense.
- Only draft expenses may be submitted.
- Only managers may approve or reject.
- Managers may act only inside their department.
- Managers may not approve or reject their own expenses.
- Only submitted expenses may be approved or rejected.
- Everything else is denied by default.

## Important warning

The `X-User-ID` header is **not real authentication**. It is intentionally used as a learning stub so IAM authorization can be studied independently. We will replace it when we reach authentication.

## Run locally

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Try the API

Identify as Noman:

```bash
curl -H 'X-User-ID: 1' http://127.0.0.1:8000/whoami
```

Read Noman's submitted expense:

```bash
curl -H 'X-User-ID: 1' http://127.0.0.1:8000/expenses/102
```

Submit Noman's draft expense:

```bash
curl -X POST -H 'X-User-ID: 1' \
  http://127.0.0.1:8000/expenses/101/submit
```

Approve Noman's submitted expense as the engineering manager:

```bash
curl -X POST -H 'X-User-ID: 2' \
  http://127.0.0.1:8000/expenses/102/approve
```

Attempt cross-department approval as the finance manager:

```bash
curl -X POST -H 'X-User-ID: 3' \
  http://127.0.0.1:8000/expenses/102/approve
```

## Run tests

```bash
pytest -q
```
