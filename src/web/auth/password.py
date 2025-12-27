"""Password hashing utilities using Argon2id."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Argon2id with secure defaults
_ph = PasswordHasher(
    time_cost=2,  # iterations
    memory_cost=65536,  # 64 MB
    parallelism=1,  # threads
    hash_len=32,  # output length
    salt_len=16,  # salt length
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: Hash to verify against

    Returns:
        True if password matches, False otherwise
    """
    try:
        _ph.verify(password_hash, password)
        # Check if hash needs rehashing (e.g., parameters changed)
        if _ph.check_needs_rehash(password_hash):
            # Note: In production, you'd want to rehash and update the DB here
            pass
        return True
    except VerifyMismatchError:
        return False
