"""Password validation utilities."""

import re


class PasswordValidationError(Exception):
    """Raised when password validation fails."""

    pass


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """Validate password against complexity requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Length check
    if len(password) < 12:
        errors.append("Password must be at least 12 characters long")

    # Uppercase check
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    # Lowercase check
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    # Digit check
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")

    # Special character check
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        errors.append(
            "Password must contain at least one special character "
            "(!@#$%^&*()_+-=[]{}|;:,.<>?)"
        )

    return (len(errors) == 0, errors)


def require_strong_password(password: str) -> None:
    """Validate password and raise exception if invalid.

    Args:
        password: Password to validate

    Raises:
        PasswordValidationError: If password doesn't meet requirements
    """
    is_valid, errors = validate_password_strength(password)
    if not is_valid:
        raise PasswordValidationError(". ".join(errors))
