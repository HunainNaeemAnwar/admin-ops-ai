"""APScheduler setup — reminder-only mode.

Per Constitution Principle I (Father-Triggered Control):
No auto-execution of any kind. Scheduler exists only to print reminders.
Father must explicitly trigger all actions via agent chat.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

scheduler = AsyncIOScheduler()


async def daily_reminder_job():
    print(f"[{datetime.now()}] REMINDER: Daily production not yet entered for today. "
          "Use the agent to record work.")


async def monthly_reminder_job():
    print(f"[{datetime.now()}] REMINDER: Month has ended. "
          "Generate payslips and send monthly report via agent.")


def setup_scheduler():
    scheduler.add_job(
        daily_reminder_job,
        CronTrigger(hour=18, minute=0),
        id="daily_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        monthly_reminder_job,
        CronTrigger(day=1, hour=9, minute=0),
        id="monthly_reminder",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[{datetime.now()}] Scheduler started (reminder-only mode). "
          "Daily reminder at 18:00, Month-end reminder at 09:00 day 1")
    print("  No auto-execution. Father triggers all actions.")
