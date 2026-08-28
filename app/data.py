from app.models import Expense, ExpenseStatus, Principal, Role, Session, UserAccount


USERS: dict[int, Principal] = {
    1: Principal(
        principal_id="user:1",
        user_id=1,
        name="Noman",
        role=Role.EMPLOYEE,
        department="engineering",
    ),
    2: Principal(
        principal_id="user:2",
        user_id=2,
        name="Aisha",
        role=Role.MANAGER,
        department="engineering",
    ),
    3: Principal(
        principal_id="user:3",
        user_id=3,
        name="Bilal",
        role=Role.MANAGER,
        department="finance",
    ),
    4: Principal(
        principal_id="user:4",
        user_id=4,
        name="Admin",
        role=Role.ADMIN,
        department="security",
    ),
}


# Development-only demo accounts. Only password hashes are stored here; the
# matching plaintext test credentials exist in the test suite, not this store.
ACCOUNTS: dict[str, UserAccount] = {
    "noman@example.com": UserAccount(
        user_id=1,
        email="noman@example.com",
        password_hash=(
            "$argon2id$v=19$m=65536,t=3,p=4$1IVrVrkVD7ewXTS4tq1wNw$"
            "Y+EthFIdOgs8B3d2plHMK8bQd3gQcpJ4Xnx8F37zYbY"
        ),
    ),
    "aisha@example.com": UserAccount(
        user_id=2,
        email="aisha@example.com",
        password_hash=(
            "$argon2id$v=19$m=65536,t=3,p=4$PYPBVZdfc4sOZSdZ56QhwA$"
            "rxipX/jC5PDQv8NiPLfDfw13JAJM1gBsMf+asCSpZiw"
        ),
    ),
    "bilal@example.com": UserAccount(
        user_id=3,
        email="bilal@example.com",
        password_hash=(
            "$argon2id$v=19$m=65536,t=3,p=4$lHKtn9jzeQgCT/svACPT2Q$"
            "ZRVP+AsQYh8MmmL1OAuv12e1MITxF/OJ9Fz6qCSdIdo"
        ),
    ),
    "admin@example.com": UserAccount(
        user_id=4,
        email="admin@example.com",
        password_hash=(
            "$argon2id$v=19$m=65536,t=3,p=4$71dqnTvJs1JmpqiKUJH16A$"
            "wkXGPJ08ZcnvJuBxC1pWGs73WU99ViqMFqKS+ln8jXQ"
        ),
    ),
}


# Keyed by SHA-256(raw bearer token), never by the raw bearer token itself.
SESSIONS: dict[str, Session] = {}


EXPENSES: dict[int, Expense] = {
    101: Expense(
        expense_id=101,
        owner_id=1,
        department="engineering",
        description="Taxi to a client meeting",
        amount=2500,
        status=ExpenseStatus.DRAFT,
    ),
    102: Expense(
        expense_id=102,
        owner_id=1,
        department="engineering",
        description="Security testing tool subscription",
        amount=12000,
        status=ExpenseStatus.SUBMITTED,
    ),
    103: Expense(
        expense_id=103,
        owner_id=2,
        department="engineering",
        description="Team lunch during an incident response",
        amount=8000,
        status=ExpenseStatus.SUBMITTED,
    ),
}
