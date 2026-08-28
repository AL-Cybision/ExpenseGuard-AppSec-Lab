from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.authentication import generate_session_token, hash_session_token
from app.data import EXPENSES, SESSIONS
from app.main import SESSION_LIFETIME, app
from app.models import ExpenseStatus, Session


client = TestClient(app)


def auth_headers(user_id: int) -> dict[str, str]:
    """Create a valid server-side session for an existing demo principal."""

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)
    created_at = datetime.now(timezone.utc)
    SESSIONS[token_hash] = Session(
        session_id=str(uuid4()),
        user_id=user_id,
        token_hash=token_hash,
        created_at=created_at,
        expires_at=created_at + SESSION_LIFETIME,
    )
    return {"Authorization": f"Bearer {raw_token}"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_x_user_id_alone_no_longer_authenticates():
    response = client.get("/whoami", headers={"X-User-ID": "1"})
    assert response.status_code == 401


def test_owner_can_read_own_expense():
    response = client.get("/expenses/102", headers=auth_headers(1))
    assert response.status_code == 200
    assert response.json()["expense"]["expense_id"] == 102


def test_employee_cannot_read_someone_elses_expense():
    response = client.get("/expenses/103", headers=auth_headers(1))
    assert response.status_code == 403


def test_owner_can_submit_draft_expense():
    response = client.post("/expenses/101/submit", headers=auth_headers(1))
    assert response.status_code == 200
    assert response.json()["expense"]["status"] == "submitted"


def test_manager_can_approve_departmental_submitted_expense():
    response = client.post("/expenses/102/approve", headers=auth_headers(2))
    assert response.status_code == 200
    assert response.json()["expense"]["status"] == "approved"


def test_manager_cannot_approve_own_expense():
    response = client.post("/expenses/103/approve", headers=auth_headers(2))
    assert response.status_code == 403


def test_denied_approval_does_not_change_expense_state():
    """A denied authenticated request must not produce the protected side effect."""

    response = client.post("/expenses/102/approve", headers=auth_headers(3))

    assert response.status_code == 403
    assert EXPENSES[102].status == ExpenseStatus.SUBMITTED
