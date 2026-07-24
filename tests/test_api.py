from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_user_is_rejected():
    response = client.get("/whoami", headers={"X-User-ID": "999"})
    assert response.status_code == 401


def test_owner_can_read_own_expense():
    response = client.get("/expenses/102", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    assert response.json()["expense"]["expense_id"] == 102


def test_employee_cannot_read_someone_elses_expense():
    response = client.get("/expenses/103", headers={"X-User-ID": "1"})
    assert response.status_code == 403


def test_owner_can_submit_draft_expense():
    response = client.post("/expenses/101/submit", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    assert response.json()["expense"]["status"] == "submitted"


def test_manager_can_approve_departmental_submitted_expense():
    response = client.post("/expenses/102/approve", headers={"X-User-ID": "2"})
    assert response.status_code == 200
    assert response.json()["expense"]["status"] == "approved"


def test_manager_cannot_approve_own_expense():
    response = client.post("/expenses/103/approve", headers={"X-User-ID": "2"})
    assert response.status_code == 403
