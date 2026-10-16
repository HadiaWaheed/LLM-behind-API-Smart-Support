from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    billing = "billing"
    technical = "technical"
    account = "account"
    delivery = "delivery"
    refund = "refund"
    other = "other"


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SuggestedTeam(str, Enum):
    billing = "billing"
    technical_support = "technical-support"
    account_support = "account-support"
    delivery = "delivery"
    general_support = "general-support"


class TriageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class TriageResponse(BaseModel):
    category: Category
    urgency: Urgency
    suggested_team: SuggestedTeam
    confidence: float = Field(..., ge=0, le=1)
    reason: str