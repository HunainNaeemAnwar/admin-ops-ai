import re
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date_str(v: str) -> str:
    if not _DATE_RE.match(v):
        raise ValueError(f"Invalid date format '{v}'. Use YYYY-MM-DD.")
    y, m, d = int(v[:4]), int(v[5:7]), int(v[8:10])
    if m < 1 or m > 12 or d < 1 or d > 31:
        raise ValueError(f"Invalid date '{v}' — day/month out of range.")
    return v


class WorkerOut(BaseModel):
    id: int
    name: str
    is_active: int = 1

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: int
    code: str
    description: str = ""
    rate: float

    class Config:
        from_attributes = True


class DailyLogEntry(BaseModel):
    id: int
    worker_name: str
    product_code: str
    quantity: int
    entry_date: str
    status: str


class DailyTotals(BaseModel):
    totals: dict[str, int] = {}
    total_pieces: int = 0


class DailyReport(BaseModel):
    date: str
    entries: list[DailyLogEntry]
    totals: dict[str, int]
    total_pieces: int


class WorkerDailyBreakdown(BaseModel):
    date: str
    status: str
    reason: str = ""
    products: dict[str, int] = {}


class WorkerMonthData(BaseModel):
    worker: str
    year: int
    month: int
    days: list[WorkerDailyBreakdown]
    source: str


class MonthlyWorkerSummary(BaseModel):
    worker: str
    totals: dict[str, int] = {}


class MonthlyReport(BaseModel):
    year: int
    month: int
    workers: list[MonthlyWorkerSummary]


class AuthUserOut(BaseModel):
    email: str = ""
    is_father: bool = False
    authenticated: bool = False


class ArchiveCheckOut(BaseModel):
    is_first_day: bool
    prev_month_archived: bool
    prev_month: dict


class StatusOut(BaseModel):
    status: str = "ok"
    message: str = ""


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


class ChatOut(BaseModel):
    status: str = "ok"
    response: str = ""


class ActionOut(BaseModel):
    status: str = "ok"
    message: str = ""


class HealthOut(BaseModel):
    status: str = "ok"
    database: str = "connected"
    workers_count: int = 0
    products_count: int = 0
    version: str = "1.0.0"
