from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class RecordWorkIn(BaseModel):
    worker: str = Field(..., min_length=1, max_length=100)
    product_code: str = Field(..., min_length=1, max_length=20)
    quantity: int = Field(..., ge=1, le=99999)

    @field_validator("product_code")
    @classmethod
    def validate_product(cls, v: str) -> str:
        valid = {"NUT", "10*20", "6*25", "6*30", "10*25"}
        if v not in valid:
            raise ValueError(f"Invalid product '{v}'. Valid: {', '.join(sorted(valid))}")
        return v


class RejectionIn(BaseModel):
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)
    product_code: str = Field(..., min_length=1, max_length=20)
    total_qty: int = Field(..., ge=1, le=999999)
    excluded_workers: str = "[]"

    @field_validator("product_code")
    @classmethod
    def validate_product(cls, v: str) -> str:
        valid = {"NUT", "10*20", "6*25", "6*30", "10*25"}
        if v not in valid:
            raise ValueError(f"Invalid product '{v}'")
        return v


class AdvanceIn(BaseModel):
    worker: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., ge=0.01, le=1_000_000)
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)
    description: str = Field(default="", max_length=500)

    @field_validator("month")
    @classmethod
    def no_future_month(cls, v: int, info) -> int:
        today = date.today()
        y = info.data.get("year", today.year)
        if y > today.year or (y == today.year and v > today.month):
            raise ValueError("Cannot record advance for a future month")
        return v


class PayslipIn(BaseModel):
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)
    worker: str = ""


class EmailReportIn(BaseModel):
    period: str = "daily"
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        if v not in ("daily", "weekly", "monthly"):
            raise ValueError("Period must be daily, weekly, or monthly")
        return v


class ChatIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default", max_length=100)
