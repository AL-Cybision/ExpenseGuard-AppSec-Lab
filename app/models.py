from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    ADMIN = "admin"


class Action(StrEnum):
    READ_EXPENSE = "expense:read"
    CREATE_EXPENSE = "expense:create"
    SUBMIT_EXPENSE = "expense:submit"
    APPROVE_EXPENSE = "expense:approve"
    REJECT_EXPENSE = "expense:reject"


class ExpenseStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Principal:
    """An identity to which roles and permissions are assigned."""

    principal_id: str
    user_id: int
    name: str
    role: Role
    department: str


@dataclass(frozen=True)
class Subject:
    """The active session acting on behalf of a principal."""

    principal: Principal
    session_id: str
    mfa_authenticated: bool = False


@dataclass
class UserAccount:
    """Authentication data associated with a human principal."""

    user_id: int
    email: str
    password_hash: str
    is_active: bool = True


@dataclass
class Expense:
    """A reimbursement request created by an employee."""

    expense_id: int
    owner_id: int
    department: str
    description: str
    amount: int
    status: ExpenseStatus = ExpenseStatus.DRAFT


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
