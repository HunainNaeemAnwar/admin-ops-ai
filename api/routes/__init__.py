from fastapi import APIRouter

router = APIRouter()
admin_router = APIRouter(prefix="/admin")

from .auth import auth_router, admin_auth_router
from .public import public_router
from .admin import admin_router as admin_dashboard_router
from .actions import actions_router
from .chat import chat_router

router.include_router(auth_router)
router.include_router(public_router)
admin_router.include_router(admin_auth_router)
admin_router.include_router(admin_dashboard_router)
admin_router.include_router(actions_router)
admin_router.include_router(chat_router)
