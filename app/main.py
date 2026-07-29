from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.authorization import authorize
from app.data import EXPENSES, USERS
from app.models import Action, Expense, ExpenseStatus, Principal, Subject


app = FastAPI(
    title="ExpenseGuard IAM Lab",
    version="0.1.0",
    description=(
        "A deliberately small expense-reimbursement API used to learn IAM, "
        "authorization, and secure application design."
    ),
)


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=3, max_length=200)
    amount: int = Field(gt=0, le=1_000_000)


class ExpenseResponse(BaseModel):
    expense_id: int
    owner_id: int
    department: str
    description: str
    amount: int
    status: ExpenseStatus


class DecisionResponse(BaseModel):
    expense: ExpenseResponse
    authorization_reason: str


def serialize_expense(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        expense_id=expense.expense_id,
        owner_id=expense.owner_id,
        department=expense.department,
        description=expense.description,
        amount=expense.amount,
        status=expense.status,
    )


def get_current_subject(
    x_user_id: int = Header(
        ...,
        alias="X-User-ID",
        description=(
            "Learning-only identity selector. This is not real authentication."
        ),
    ),
) -> Subject:
    principal: Principal | None = USERS.get(x_user_id)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown user. Supply a valid X-User-ID header.",
        )

    return Subject(
        principal=principal,
        session_id=f"lab-session-{uuid4()}",
        mfa_authenticated=False,
    )


def get_expense_or_404(expense_id: int) -> Expense:
    expense = EXPENSES.get(expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found.")
    return expense


def enforce(subject: Subject, action: Action, expense: Expense) -> str:
    decision = authorize(subject, action, expense)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    return decision.reason


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/whoami")
def whoami(subject: Subject = Depends(get_current_subject)) -> dict[str, object]:
    principal = subject.principal
    return {
        "principal_id": principal.principal_id,
        "user_id": principal.user_id,
        "name": principal.name,
        "role": principal.role,
        "department": principal.department,
        "session_id": subject.session_id,
        "warning": "X-User-ID is a learning stub, not real authentication.",
    }


@app.post("/expenses", response_model=ExpenseResponse, status_code=201)
def create_expense(
    payload: ExpenseCreate,
    subject: Subject = Depends(get_current_subject),
) -> ExpenseResponse:
    principal = subject.principal
    next_id = max(EXPENSES, default=100) + 1

    expense = Expense(
        expense_id=next_id,
        owner_id=principal.user_id,
        department=principal.department,
        description=payload.description,
        amount=payload.amount,
        status=ExpenseStatus.DRAFT,
    )
    EXPENSES[next_id] = expense
    return serialize_expense(expense)


@app.get("/expenses/{expense_id}", response_model=DecisionResponse)
def read_expense(
    expense_id: int,
    subject: Subject = Depends(get_current_subject),
) -> DecisionResponse:
    expense = get_expense_or_404(expense_id)
    reason = enforce(subject, Action.READ_EXPENSE, expense)
    return DecisionResponse(
        expense=serialize_expense(expense),
        authorization_reason=reason,
    )


@app.post("/expenses/{expense_id}/submit", response_model=DecisionResponse)
def submit_expense(
    expense_id: int,
    subject: Subject = Depends(get_current_subject),
) -> DecisionResponse:
    expense = get_expense_or_404(expense_id)
    reason = enforce(subject, Action.SUBMIT_EXPENSE, expense)
    expense.status = ExpenseStatus.SUBMITTED
    return DecisionResponse(
        expense=serialize_expense(expense),
        authorization_reason=reason,
    )


@app.post("/expenses/{expense_id}/approve", response_model=DecisionResponse)
def approve_expense(
    expense_id: int,
    subject: Subject = Depends(get_current_subject),
) -> DecisionResponse:
    expense = get_expense_or_404(expense_id)

    # SECURE ORDER: authorize before performing the protected state change.
    reason = enforce(subject, Action.APPROVE_EXPENSE, expense)
    expense.status = ExpenseStatus.APPROVED

    # SECURITY LAB — deliberately vulnerable ordering (keep commented in Git):
    #
    # To reproduce the bug later:
    # 1. Comment out the two secure lines above.
    # 2. Uncomment the two lines below.
    # 3. Run:
    #    python -m pytest -v \
    #      tests/test_api.py::test_denied_approval_does_not_change_expense_state
    #
    # The endpoint returns 403 for an unauthorized manager, but the expense has
    # already been changed to APPROVED because the side effect happened first.
    #
    # expense.status = ExpenseStatus.APPROVED
    # reason = enforce(subject, Action.APPROVE_EXPENSE, expense)

    return DecisionResponse(
        expense=serialize_expense(expense),
        authorization_reason=reason,
    )


@app.post("/expenses/{expense_id}/reject", response_model=DecisionResponse)
def reject_expense(
    expense_id: int,
    subject: Subject = Depends(get_current_subject),
) -> DecisionResponse:
    expense = get_expense_or_404(expense_id)
    reason = enforce(subject, Action.REJECT_EXPENSE, expense)
    expense.status = ExpenseStatus.REJECTED
    return DecisionResponse(
        expense=serialize_expense(expense),
        authorization_reason=reason,
    )
