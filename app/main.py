from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.authentication import (
    DUMMY_PASSWORD_HASH,
    extract_bearer_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    normalize_email,
    password_needs_rehash,
    verify_password,
)
from app.authorization import authorize
from app.data import ACCOUNTS, EXPENSES, SESSIONS, USERS
from app.models import Action, Expense, ExpenseStatus, Principal, Session, Subject


SESSION_LIFETIME = timedelta(hours=8)
AUTHENTICATION_ERROR_DETAIL = "Invalid or missing authentication credentials."


app = FastAPI(
    title="ExpenseGuard IAM Lab",
    version="0.1.0",
    description=(
        "A deliberately small expense-reimbursement API used to learn IAM, "
        "authorization, and secure application design."
    ),
)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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


def authentication_error() -> HTTPException:
    """Return a generic bearer-authentication failure without leaking state."""

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=AUTHENTICATION_ERROR_DETAIL,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_session(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Session:
    """Resolve and validate the server-side session for a bearer credential."""

    raw_token = extract_bearer_token(authorization)
    if raw_token is None:
        raise authentication_error()

    token_hash = hash_session_token(raw_token)
    session = SESSIONS.get(token_hash)
    if session is None:
        raise authentication_error()

    now = datetime.now(timezone.utc)
    if session.revoked_at is not None or now >= session.expires_at:
        raise authentication_error()

    return session


def get_current_subject(
    session: Session = Depends(get_current_session),
) -> Subject:
    """Construct the active Subject only from a validated server-side session."""

    account = next(
        (candidate for candidate in ACCOUNTS.values() if candidate.user_id == session.user_id),
        None,
    )
    if account is None or not account.is_active:
        raise authentication_error()

    principal: Principal | None = USERS.get(session.user_id)
    if principal is None:
        raise authentication_error()

    return Subject(
        principal=principal,
        session_id=session.session_id,
        mfa_authenticated=session.mfa_authenticated,
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


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    email = normalize_email(payload.email)
    account = ACCOUNTS.get(email)

    password_hash = (
        account.password_hash if account is not None else DUMMY_PASSWORD_HASH
    )
    password_valid = verify_password(password_hash, payload.password)

    if account is None or not password_valid or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if password_needs_rehash(account.password_hash):
        account.password_hash = hash_password(payload.password)

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    created_at = datetime.now(timezone.utc)

    session = Session(
        session_id=str(uuid4()),
        user_id=account.user_id,
        token_hash=token_hash,
        created_at=created_at,
        expires_at=created_at + SESSION_LIFETIME,
    )
    SESSIONS[token_hash] = session

    return LoginResponse(access_token=raw_token)


@app.post("/auth/logout")
def logout(session: Session = Depends(get_current_session)) -> dict[str, str]:
    session.revoked_at = datetime.now(timezone.utc)
    return {"status": "logged_out"}


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
        "mfa_authenticated": subject.mfa_authenticated,
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
