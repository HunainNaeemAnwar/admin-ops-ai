from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from api.schemas import ChatIn, ChatOut
from api.routes.common import CurrentUser, require_admin, require_csrf

chat_router = APIRouter()


@chat_router.post("/chat", response_model=ChatOut)
async def admin_agent_chat(data: ChatIn, user: CurrentUser, request: Request) -> ChatOut:
    require_admin(user)
    require_csrf(request)
    from my_agents.orchestrator.agent import chat
    result = await chat(data.text)
    return ChatOut(response=result)


@chat_router.post("/chat/stream")
async def admin_agent_chat_stream(data: ChatIn, user: CurrentUser, request: Request) -> StreamingResponse:
    require_admin(user)
    require_csrf(request)
    from my_agents.orchestrator.agent import stream_chat
    return StreamingResponse(
        stream_chat(data.text, session_id=data.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.get("/chat/sessions")
async def admin_chat_sessions(user: CurrentUser) -> list[dict]:
    require_admin(user)
    from services.database import list_chat_sessions
    return list_chat_sessions()


@chat_router.get("/chat/sessions/{session_id}")
async def admin_chat_session_detail(session_id: str, user: CurrentUser) -> list:
    require_admin(user)
    from services.database import load_chat_messages, _extract_text
    items = load_chat_messages(session_id)
    for item in items:
        item["content"] = _extract_text(item)
    return items


@chat_router.delete("/chat/sessions/{session_id}")
async def admin_chat_session_delete(session_id: str, user: CurrentUser, request: Request) -> dict:
    require_admin(user)
    require_csrf(request)
    from my_agents.orchestrator.agent import _remove_memory
    await _remove_memory(session_id)
    return {"status": "deleted"}


@chat_router.post("/chat/sessions/{session_id}/forget")
async def admin_chat_session_forget(session_id: str, user: CurrentUser, request: Request) -> dict:
    require_admin(user)
    require_csrf(request)
    from my_agents.orchestrator.agent import _forget_memory
    await _forget_memory(session_id)
    return {"status": "forgotten"}
