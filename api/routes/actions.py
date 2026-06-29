import json
from datetime import date

from fastapi import APIRouter, Request

from api.schemas import ActionOut, RecordWorkIn, RejectionIn, AdvanceIn, PayslipIn, EmailReportIn
from api.routes.common import CurrentUser, require_admin, require_csrf
from services.production_tools import log_production_json
from services.rejection_tools import log_rejection as rej_log
from services.advance_tools import record_advance as adv_rec
from services.email_tools import send_report
from services.database import backfill_history

actions_router = APIRouter()


@actions_router.post("/record", response_model=ActionOut)
async def admin_record_work(
    data: RecordWorkIn,
    user: CurrentUser,
    request: Request = None,
) -> ActionOut:
    require_admin(user)
    require_csrf(request)
    entry = json.dumps({"worker": data.worker, "product_code": data.product_code, "quantity": data.quantity})
    result = log_production_json(f"[{entry}]")
    return ActionOut(message=result)


@actions_router.post("/rejection", response_model=ActionOut)
async def admin_add_rejection(data: RejectionIn, user: CurrentUser, request: Request) -> ActionOut:
    require_admin(user)
    require_csrf(request)
    excluded = json.loads(data.excluded_workers)
    result = rej_log(data.year, data.month, data.product_code, data.total_qty, excluded)
    return ActionOut(message=result)


@actions_router.post("/advance", response_model=ActionOut)
async def admin_add_advance(data: AdvanceIn, user: CurrentUser, request: Request) -> ActionOut:
    require_admin(user)
    require_csrf(request)
    result = adv_rec(data.worker, data.amount, data.year, data.month, data.description)
    return ActionOut(message=result)


@actions_router.post("/payslip", response_model=ActionOut)
async def admin_generate_payslip(data: PayslipIn, user: CurrentUser, request: Request) -> ActionOut:
    require_admin(user)
    require_csrf(request)
    from my_agents.orchestrator.agent import generate_payslip_tool
    result = generate_payslip_tool(data.year, data.month, data.worker or None)
    return ActionOut(message=result)


@actions_router.post("/email", response_model=ActionOut)
async def admin_send_email_report(data: EmailReportIn, user: CurrentUser, request: Request) -> ActionOut:
    require_admin(user)
    require_csrf(request)
    today = date.today()
    result = send_report(data.period, data.year or today.year, data.month or today.month, data.day or today.day)
    return ActionOut(message=result)


@actions_router.post("/backfill")
async def admin_backfill(user: CurrentUser, request: Request) -> dict:
    require_admin(user)
    require_csrf(request)
    return backfill_history()
