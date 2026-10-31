"""Authentication API endpoints."""
import logging
from uuid import uuid4
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.user import User
from app.db import memory_store
from app.schemas.user import (
    UserCreate,
    UserResponse,
    LoginRequest,
    Token,
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# Flag to track if we're using in-memory storage
USE_IN_MEMORY = False


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    global USE_IN_MEMORY

    # Try database first, fall back to in-memory
    try:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = User(
            id=str(uuid4()),
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
    except HTTPException:
        raise  # Always propagate intentional HTTP errors
    except Exception as e:
        logger.warning(f"Database unavailable, using in-memory storage: {e}")
        USE_IN_MEMORY = True

        existing = memory_store.get_user_by_email(user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = memory_store.create_user(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
        )

        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user.get("full_name"),
            is_active=user["is_active"],
            created_at=datetime.fromisoformat(user["created_at"]),
        )


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return access token."""
    global USE_IN_MEMORY

    try:
        result = await db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()

        if not user or not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        access_token = create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        return Token(access_token=access_token)
    except HTTPException:
        raise  # Always propagate intentional HTTP errors
    except Exception as e:
        logger.warning(f"Database unavailable, using in-memory storage: {e}")
        USE_IN_MEMORY = True

        user = memory_store.get_user_by_email(login_data.email)

        if not user or not user.get("hashed_password"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(login_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        access_token = create_access_token(
            data={"sub": user["id"], "email": user["email"]}
        )
        return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user information."""
    global USE_IN_MEMORY

    if USE_IN_MEMORY:
        user = memory_store.get_user_by_id(current_user["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user.get("full_name"),
            is_active=user["is_active"],
            created_at=datetime.fromisoformat(user["created_at"]),
        )

    try:
        result = await db.execute(
            select(User).where(User.id == current_user["user_id"])
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user
    except HTTPException:
        raise  # Always propagate intentional HTTP errors
    except Exception as e:
        logger.warning(f"Database unavailable, using in-memory storage: {e}")
        USE_IN_MEMORY = True

        user = memory_store.get_user_by_id(current_user["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user.get("full_name"),
            is_active=user["is_active"],
            created_at=datetime.fromisoformat(user["created_at"]),
        )