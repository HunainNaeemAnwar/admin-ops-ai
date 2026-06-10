import asyncio
from datetime import date, datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tools.calc_tools import calc_daily_summary, calc_monthly_summary
from tools.email_tools import send_daily_summary
from tools.payslip_tools import generate_pdf_payslip, generate_excel_payslip
from tools.excel_tools import get_all_workers

scheduler = AsyncIOScheduler()


async def daily_summary_job():
    today = date.today()
    summary = calc_daily_summary(today.year, today.month, today.day)
    if summary["entries_count"] > 0:
        result = send_daily_summary(today.year, today.month, today.day, summary)
        print(f"[{datetime.now()}] Daily summary sent: {result}")
    else:
        print(f"[{datetime.now()}] No entries for today, skipping email")


async def monthly_payslips_job():
    today = date.today()
    yesterday_month = (today.replace(day=1) - __import__("datetime").timedelta(days=1))
    year = yesterday_month.year
    month = yesterday_month.month
    workers = get_all_workers(year, month)
    if not workers:
        print(f"[{datetime.now()}] No workers for {year}-{month:02d}, skipping payslips")
        return
    for worker in workers:
        pdf = generate_pdf_payslip(worker, year, month)
        xls = generate_excel_payslip(worker, year, month)
        print(f"[{datetime.now()}] Pay slip: {worker} -> {pdf}, {xls}")


def setup_scheduler():
    scheduler.add_job(
        daily_summary_job,
        CronTrigger(hour=18, minute=0),
        id="daily_summary",
        replace_existing=True,
    )
    scheduler.add_job(
        monthly_payslips_job,
        CronTrigger(day=1, hour=9, minute=0),
        id="monthly_payslips",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[{datetime.now()}] Scheduler started. Daily at 18:00, Month-end at 09:00 day 1")
