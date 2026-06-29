"""
app/models.py — Shared Pydantic models for the Car entity and Chat system.

All models use Pydantic v2 syntax and include field-level validation.
Importable via: from app.models import Car, CarCreate, CarResponse, CarListResponse

Chat models:
    from app.models import ChatRole, ChatMessage, ChatConversation, ChatRequest, ChatResponse
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class Car(BaseModel):
    """
    Core Car entity representing a single car in the store.

    This is the canonical data model. Every field is required and
    validated according to the business rules below.
    """

    id: str = Field(
        ...,
        description="Unique identifier for the car (UUID v4 string, auto-generated on creation).",
    )
    brand: str = Field(
        ...,
        min_length=1,
        description="Car manufacturer/brand name. Must be a non-empty string.",
    )
    model: str = Field(
        ...,
        min_length=1,
        description="Car model name. Must be a non-empty string.",
    )
    year: int = Field(
        ...,
        ge=1886,
        description="Manufacturing year. Must be >= 1886 (first car invented) and <= current year.",
    )
    km: int = Field(
        ...,
        ge=0,
        description="Total kilometres driven. Must be >= 0.",
    )
    price: float = Field(
        ...,
        ge=0.0,
        description="Price in EUR. Must be >= 0.",
    )
    image_url: str = Field(
        ...,
        description="URL or relative path to the car's image file (e.g. '/uploads/car_uuid.jpg').",
    )

    # ---- Field validators ----

    @field_validator("brand")
    @classmethod
    def brand_must_be_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("brand must be a non-empty string")
        return stripped

    @field_validator("model")
    @classmethod
    def model_must_be_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("model must be a non-empty string")
        return stripped

    @field_validator("year")
    @classmethod
    def year_must_be_valid(cls, v: int) -> int:
        current_year = datetime.now(timezone.utc).year
        if v < 1886:
            raise ValueError("year must be >= 1886 (the year the first car was invented)")
        if v > current_year:
            raise ValueError(f"year must not exceed the current year ({current_year})")
        return v

    @field_validator("km")
    @classmethod
    def km_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("km must be >= 0")
        return v

    @field_validator("price")
    @classmethod
    def price_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price must be >= 0")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "brand": "Toyota",
                "model": "Corolla",
                "year": 2020,
                "km": 45000,
                "price": 18500.0,
                "image_url": "/uploads/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
            }
        }


class CarCreate(BaseModel):
    """
    Request schema for creating a new car.

    Contains all Car fields EXCEPT `id`, which is auto-generated
    on the server side (UUID v4).
    """

    brand: str = Field(
        ...,
        min_length=1,
        description="Car manufacturer/brand name. Must be a non-empty string.",
    )
    model: str = Field(
        ...,
        min_length=1,
        description="Car model name. Must be a non-empty string.",
    )
    year: int = Field(
        ...,
        ge=1886,
        description="Manufacturing year. Must be >= 1886 and <= current year.",
    )
    km: int = Field(
        ...,
        ge=0,
        description="Total kilometres driven. Must be >= 0.",
    )
    price: float = Field(
        ...,
        ge=0.0,
        description="Price in EUR. Must be >= 0.",
    )
    image_url: str = Field(
        ...,
        description="URL or relative path to the car's image file.",
    )

    # Reuse the same validators as Car
    _brand_validator = field_validator("brand")(Car.brand_must_be_non_empty)
    _model_validator = field_validator("model")(Car.model_must_be_non_empty)
    _year_validator = field_validator("year")(Car.year_must_be_valid)
    _km_validator = field_validator("km")(Car.km_must_be_non_negative)
    _price_validator = field_validator("price")(Car.price_must_be_non_negative)

    class Config:
        json_schema_extra = {
            "example": {
                "brand": "Toyota",
                "model": "Corolla",
                "year": 2020,
                "km": 45000,
                "price": 18500.0,
                "image_url": "/uploads/placeholder.jpg",
            }
        }


class CarResponse(BaseModel):
    """
    API response wrapper for a single Car.

    Returns the full Car object under the `car` key.
    """

    car: Car = Field(..., description="The requested car object.")

    class Config:
        json_schema_extra = {
            "example": {
                "car": {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "brand": "Toyota",
                    "model": "Corolla",
                    "year": 2020,
                    "km": 45000,
                    "price": 18500.0,
                    "image_url": "/uploads/a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg",
                }
            }
        }


class CarListResponse(BaseModel):
    """
    API response wrapper for a list of Cars.

    Returns the array of Car objects under the `cars` key.
    """

    cars: List[Car] = Field(..., description="List of car objects.")

    class Config:
        json_schema_extra = {
            "example": {
                "cars": [
                    {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "brand": "Toyota",
                        "model": "Corolla",
                        "year": 2020,
                        "km": 45000,
                        "price": 18500.0,
                        "image_url": "/uploads/car1.jpg",
                    },
                    {
                        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "brand": "BMW",
                        "model": "X5",
                        "year": 2022,
                        "km": 12000,
                        "price": 52000.0,
                        "image_url": "/uploads/car2.jpg",
                    },
                ]
            }
        }


# =============================================================================
# Chat / Conversation models
# =============================================================================


class ChatRole(str, Enum):
    """
    Enumeration of allowed roles in a chat message.

    - `user`: a message sent by the human user.
    - `assistant`: a message generated by the AI assistant.
    """

    user = "user"
    assistant = "assistant"


class ChatMessage(BaseModel):
    """
    A single message in a chat conversation.

    Fields:
        role: Who sent the message — either "user" or "assistant".
        content: The textual content of the message. Must be non-empty.
        timestamp: UTC datetime when the message was created (auto-set on construction).
    """

    role: ChatRole = Field(
        ...,
        description="Role of the message sender. One of: 'user', 'assistant'.",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="The textual content of the message. Must be a non-empty string.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the message was created (auto-set).",
    )

    # ---- Field validators ----

    @field_validator("content")
    @classmethod
    def content_must_be_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("content must be a non-empty string")
        return stripped

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What cars do you have under \u20ac20,000?",
                "timestamp": "2025-01-15T14:30:00Z",
            }
        }


class ChatConversation(BaseModel):
    """
    A chat conversation containing a sequence of messages.

    Fields:
        id: Unique UUID v4 identifier for the conversation (auto-generated).
        title: Human-readable title for the conversation (e.g. "Question about SUVs").
        messages: Ordered list of ChatMessage objects that form the conversation.
        created_at: UTC datetime when the conversation was first created (auto-set).
        updated_at: UTC datetime when the conversation was last updated (auto-set).
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the conversation (UUID v4 string, auto-generated).",
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Human-readable title for the conversation. Must be non-empty.",
    )
    messages: List[ChatMessage] = Field(
        default_factory=list,
        description="Ordered list of messages in the conversation.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the conversation was created (auto-set).",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the conversation was last updated (auto-set).",
    )

    # ---- Field validators ----

    @field_validator("title")
    @classmethod
    def title_must_be_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("title must be a non-empty string")
        return stripped

    class Config:
        json_schema_extra = {
            "example": {
                "id": "c9b1d2e3-f4a5-6789-bcde-f01234567890",
                "title": "Question about SUVs",
                "messages": [
                    {
                        "role": "user",
                        "content": "What cars do you have under \u20ac20,000?",
                        "timestamp": "2025-01-15T14:30:00Z",
                    },
                    {
                        "role": "assistant",
                        "content": "We have several options under \u20ac20,000...",
                        "timestamp": "2025-01-15T14:30:05Z",
                    },
                ],
                "created_at": "2025-01-15T14:30:00Z",
                "updated_at": "2025-01-15T14:30:05Z",
            }
        }


class ChatRequest(BaseModel):
    """
    Request schema for POST /api/chat.

    Fields:
        conversation_id: UUID string of an existing conversation, or null to start a new one.
        message: The user's message text. Must be non-empty.
    """

    conversation_id: Optional[str] = Field(
        None,
        description="UUID of an existing conversation to continue, or null to start a new conversation.",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="The user's message text. Must be non-empty.",
    )

    @field_validator("message")
    @classmethod
    def message_must_be_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message must be a non-empty string")
        return stripped

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": None,
                "message": "What cars do you have?",
            }
        }


class ChatResponse(BaseModel):
    """
    Response schema for POST /api/chat (non-streaming variant).

    Fields:
        conversation_id: UUID string of the conversation.
        reply: The assistant's full reply text.
    """

    conversation_id: str = Field(
        ...,
        description="UUID of the conversation this reply belongs to.",
    )
    reply: str = Field(
        ...,
        description="The assistant's full reply text.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "c9b1d2e3-f4a5-6789-bcde-f01234567890",
                "reply": "Here are the cars we currently have available...",
            }
        }


class ConversationListItem(BaseModel):
    """
    Summary model for listing conversations.

    Fields:
        id: UUID string of the conversation.
        title: Human-readable title.
        updated_at: UTC timestamp of last update.
    """

    id: str = Field(..., description="UUID of the conversation.")
    title: str = Field(..., description="Human-readable title.")
    updated_at: datetime = Field(
        ..., description="UTC timestamp of when the conversation was last updated."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "c9b1d2e3-f4a5-6789-bcde-f01234567890",
                "title": "Question about SUVs",
                "updated_at": "2025-01-15T14:30:05Z",
            }
        }
