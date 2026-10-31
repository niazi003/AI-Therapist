"""Pydantic schemas for request and response validation."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# Base schemas
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Auth schemas
class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


# Consent schemas
class ConsentBase(BaseModel):
    """Base consent schema."""
    purpose: str
    policy_version: str = "1.0"


class ConsentCreate(ConsentBase):
    """Schema for creating consent."""
    granted: bool = True


class ConsentUpdate(BaseModel):
    """Schema for updating consent."""
    granted: bool


class ConsentResponse(ConsentBase):
    """Consent response schema."""
    id: str
    user_id: str
    granted: bool
    granted_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# Chat schemas
class ChatMessage(BaseModel):
    """Incoming chat message schema."""
    message: str = Field(..., min_length=1, max_length=10000)
    country_code: Optional[str] = Field(default=None, pattern=r"^[A-Za-z]{2}$")


class ChatResponse(BaseModel):
    """Chat response schema."""
    workflow: str  # routine, follow_up, urgent, professional_referral, review_unavailable
    message: str
    clarifying_question: Optional[str] = None
    urgent_help_info: Optional[str] = None
    service_unavailable: bool = False
    support_url: Optional[str] = None


# Memory schemas
class MemoryBase(BaseModel):
    """Base memory schema."""
    content: str


class MemoryResponse(MemoryBase):
    """Memory response schema."""
    id: str
    memory_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryUpdate(BaseModel):
    """Schema for updating memory."""
    content: str


# Appointment schemas
class ProviderBase(BaseModel):
    """Base provider schema."""
    id: str
    name: str
    specialty: str
    location: str


class ProviderSlot(BaseModel):
    """Provider availability slot."""
    slot_id: str
    start_time: datetime
    end_time: datetime
    is_available: bool


class ProviderResponse(ProviderBase):
    """Provider response with availability."""
    slots: list[ProviderSlot] = []
    is_simulated: bool = True

    model_config = {"from_attributes": True}


class AppointmentCreate(BaseModel):
    """Schema for creating an appointment."""
    provider_id: str
    slot_id: str
    idempotency_key: str


class AppointmentResponse(BaseModel):
    """Appointment response schema."""
    id: str
    provider_id: str
    provider_name: str
    appointment_time: datetime
    status: str
    is_simulated: bool
    external_confirmation: Optional[str]

    model_config = {"from_attributes": True}


# Health check schema
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    services: dict[str, str]