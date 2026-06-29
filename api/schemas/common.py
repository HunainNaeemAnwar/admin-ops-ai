import re
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

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
    is_admin: bool = False
    authenticated: bool = False
    token: str = ""


class ArchiveCheckOut(BaseModel):
    is_first_day: bool
    prev_month_archived: bool
    prev_month: dict


class StatusOut(BaseModel):
    status: str = "ok"
    message: str = ""


class HealthOut(BaseModel):
    status: str = "ok"
    database: str = "connected"
    workers_count: int = 0
    products_count: int = 0
    version: str = "1.0.0"


class ChatOut(BaseModel):
    status: str = "ok"
    response: str = ""


class ActionOut(BaseModel):
    status: str = "ok"
    message: str = ""
