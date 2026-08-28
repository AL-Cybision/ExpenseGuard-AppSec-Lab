import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


password_hasher = PasswordHasher()

# Valid Argon2 work for unknown accounts reduces obvious username-enumeration
# timing differences. Generate this once when the process starts, not per login.
_dummy_password = secrets.token_urlsafe(32)
DUMMY_PASSWORD_HASH = password_hasher.hash(_dummy_password)
del _dummy_password


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


def normalize_email(email: str) -> str:
    """Normalize ExpenseGuard's email login identifier for consistent lookup."""

    return email.strip().lower()


def generate_session_token() -> str:
    """Return a fresh high-entropy opaque bearer token."""

    return secrets.token_urlsafe(32)


def hash_session_token(raw_token: str) -> str:
    """Hash a high-entropy session token for server-side lookup and storage."""

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def extract_bearer_token(authorization: str | None) -> str | None:
    """Return a bearer credential from an Authorization header, if well formed."""

    if authorization is None:
        return None

    parts = authorization.split()
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer" or not token:
        return None

    return token
