from app.models import Action, Decision, Expense, ExpenseStatus, Role, Subject


def allow(reason: str) -> Decision:
    return Decision(allowed=True, reason=reason)


def deny(reason: str) -> Decision:
    return Decision(allowed=False, reason=reason)


def authorize(subject: Subject, action: Action, expense: Expense) -> Decision:
    """Return an explicit authorization decision for one action and resource."""

    principal = subject.principal

    if action == Action.READ_EXPENSE:
        if principal.role == Role.ADMIN:
            return allow("Administrators may read every expense.")

        if expense.owner_id == principal.user_id:
            return allow("Employees may read their own expenses.")

        if (
            principal.role == Role.MANAGER
            and principal.department == expense.department
        ):
            return allow("Managers may read expenses in their own department.")

        return deny("The expense is outside the subject's permitted scope.")

    if action == Action.SUBMIT_EXPENSE:
        if expense.owner_id != principal.user_id:
            return deny("Employees may not submit another user's expense.")

        if expense.status != ExpenseStatus.DRAFT:
            return deny("Only draft expenses may be submitted.")

        return allow("The owner may submit their draft expense for review.")

    if action == Action.APPROVE_EXPENSE:
        if principal.role != Role.MANAGER:
            return deny("Only managers may approve expenses.")

        if principal.department != expense.department:
            return deny("Managers may approve only expenses in their department.")

        if principal.user_id == expense.owner_id:
            return deny("Managers may not approve their own expenses.")

        if expense.status != ExpenseStatus.SUBMITTED:
            return deny("Only submitted expenses may be approved.")

        return allow("The manager may approve this submitted departmental expense.")

    if action == Action.REJECT_EXPENSE:
        if principal.role != Role.MANAGER:
            return deny("Only managers may reject expenses.")

        if principal.department != expense.department:
            return deny("Managers may reject only expenses in their department.")

        if principal.user_id == expense.owner_id:
            return deny("Managers may not reject their own expenses.")

        if expense.status != ExpenseStatus.SUBMITTED:
            return deny("Only submitted expenses may be rejected.")

        return allow("The manager may reject this submitted departmental expense.")

    return deny("No policy explicitly allows this action.")
