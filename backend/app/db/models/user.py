"""Database models for the application."""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Boolean, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Application user model."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    consent_records: Mapped[list["ConsentRecord"]] = relationship(
        "ConsentRecord", back_populates="user", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    user_profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class ConsentRecord(Base):
    """Consent record for user data processing."""
    
    __tablename__ = "consent_records"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="consent_records")


class Appointment(Base):
    """Appointment booking records."""
    
    __tablename__ = "appointments"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slot_id: Mapped[str] = mapped_column(String(255), nullable=False)
    appointment_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, confirmed, cancelled, completed
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    external_confirmation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="appointments")


class Conversation(Base):
    """Conversation sessions."""
    
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    summary: Mapped[Optional["ConversationSummary"]] = relationship(
        "ConversationSummary", back_populates="conversation", uselist=False,
        cascade="all, delete-orphan"
    )


class Message(Base):
    """Individual messages in conversations."""
    
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), 
        nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_state: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # routine, follow_up, urgent, review_unavailable
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )


class ConversationSummary(Base):
    """Summarized conversation for efficient context retrieval."""
    
    __tablename__ = "conversation_summaries"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_topics: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of topics
    emotional_state: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Overall emotional state from conversation
    action_items: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of action items
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="summary"
    )


class UserProfile(Base):
    """User profile with extracted insights and preferences."""
    
    __tablename__ = "user_profiles"
    
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    
    # Profile information extracted from conversations
    preferences: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON object with user preferences
    important_context: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Key context to remember
    goals: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # User's stated goals
    challenges: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Ongoing challenges user is facing
    support_preferences: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # How user prefers to receive support
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_profile")
