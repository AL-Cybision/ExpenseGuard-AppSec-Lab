from argon2 import PasswordHasher

from app.authentication import hash_password, password_needs_rehash, verify_password


TEST_PASSWORD = "ExpenseGuard Test Password 2026"


def test_hash_password_does_not_return_plaintext():
    password_hash = hash_password(TEST_PASSWORD)
    assert password_hash != TEST_PASSWORD


def test_password_hash_uses_argon2id():
    password_hash = hash_password(TEST_PASSWORD)
    assert password_hash.startswith("$argon2id$")


def test_correct_password_verifies():
    password_hash = hash_password(TEST_PASSWORD)
    assert verify_password(password_hash, TEST_PASSWORD) is True


def test_wrong_password_is_rejected():
    password_hash = hash_password(TEST_PASSWORD)
    assert verify_password(password_hash, "Another Test Password 2026") is False


def test_same_password_produces_different_hashes():
    first_hash = hash_password(TEST_PASSWORD)
    second_hash = hash_password(TEST_PASSWORD)

    assert first_hash != second_hash
    assert verify_password(first_hash, TEST_PASSWORD) is True
    assert verify_password(second_hash, TEST_PASSWORD) is True


def test_outdated_parameters_are_detected_for_rehash():
    legacy_hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    legacy_hash = legacy_hasher.hash(TEST_PASSWORD)

    assert password_needs_rehash(legacy_hash) is True
