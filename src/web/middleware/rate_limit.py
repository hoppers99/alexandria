"""Rate limiting middleware for Alexandria."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Default rate limit for all endpoints
    storage_uri="memory://",  # In-memory storage (could use Redis in production)
)
