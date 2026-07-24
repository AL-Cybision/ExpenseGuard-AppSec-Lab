from app.models import Expense, ExpenseStatus, Principal, Role


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
