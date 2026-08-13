from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an Argon2id hash for a plaintext password."""

    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True only when the submitted password matches the stored hash."""

    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """Return whether the stored Argon2 hash uses outdated parameters."""

    return password_hasher.check_needs_rehash(password_hash)
