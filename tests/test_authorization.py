from app.authorization import authorize
from app.data import EXPENSES, USERS
from app.models import Action, Subject


def subject(user_id: int) -> Subject:
    return Subject(
        principal=USERS[user_id],
        session_id=f"test-session-{user_id}",
    )


def test_owner_can_read_own_expense():
    decision = authorize(subject(1), Action.READ_EXPENSE, EXPENSES[102])
    assert decision.allowed is True


def test_employee_cannot_read_manager_expense():
    decision = authorize(subject(1), Action.READ_EXPENSE, EXPENSES[103])
    assert decision.allowed is False


def test_same_department_manager_can_approve_submitted_expense():
    decision = authorize(subject(2), Action.APPROVE_EXPENSE, EXPENSES[102])
    assert decision.allowed is True


def test_manager_cannot_approve_own_expense():
    decision = authorize(subject(2), Action.APPROVE_EXPENSE, EXPENSES[103])
    assert decision.allowed is False
    assert "own" in decision.reason.lower()


def test_cross_department_manager_cannot_approve_expense():
    decision = authorize(subject(3), Action.APPROVE_EXPENSE, EXPENSES[102])
    assert decision.allowed is False
    assert "department" in decision.reason.lower()


def test_non_manager_cannot_approve_expense():
    decision = authorize(subject(1), Action.APPROVE_EXPENSE, EXPENSES[102])
    assert decision.allowed is False
