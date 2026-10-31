"""In-memory user store for development when database is unavailable."""
import threading
from typing import Optional
from uuid import uuid4
from datetime import datetime

# In-memory storage (for development only)
_users: dict[str, dict] = {}
_users_by_email: dict[str, str] = {}  # email -> user_id
_lock = threading.Lock()


def create_user(email: str, password_hash: str, full_name: Optional[str] = None) -> dict:
    """Create a new user in memory."""
    with _lock:
        user_id = str(uuid4())
        user = {
            "id": user_id,
            "email": email,
            "hashed_password": password_hash,
            "full_name": full_name,
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),

        }
        _users[user_id] = user
        _users_by_email[email] = user_id
        return user


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by ID."""
    return _users.get(user_id)


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    user_id = _users_by_email.get(email)
    if user_id:
        return _users.get(user_id)
    return None


def update_user(user_id: str, **kwargs) -> Optional[dict]:
    """Update user fields."""
    with _lock:
        if user_id in _users:
            _users[user_id].update(kwargs)
            _users[user_id]["updated_at"] = datetime.utcnow().isoformat()
            return _users[user_id]
    return None


def delete_user(user_id: str) -> bool:
    """Delete a user."""
    with _lock:
        if user_id in _users:
            user = _users[user_id]
            email = user.get("email")
            if email and email in _users_by_email:
                del _users_by_email[email]
            del _users[user_id]
            return True
    return False