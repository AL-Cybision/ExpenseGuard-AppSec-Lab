from copy import deepcopy

import pytest

from app.data import EXPENSES


@pytest.fixture(autouse=True)
def restore_expenses():
    original = deepcopy(EXPENSES)
    yield
    EXPENSES.clear()
    EXPENSES.update(original)
