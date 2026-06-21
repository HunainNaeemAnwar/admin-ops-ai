from pathlib import Path
from agents import SQLiteSession

MEMORY_DIR = Path("data/agent_memory")
MEMORY_DB = str(MEMORY_DIR / "agent_memory.db")


class ConversationMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._session = SQLiteSession(session_id, MEMORY_DB)

    @property
    def session(self) -> SQLiteSession:
        return self._session

    async def turn_count(self) -> int:
        items = await self._session.get_items()
        return len(items)

    async def compact(self) -> str:
        items = await self._session.get_items()
        before = len(items)
        if before <= 4:
            return "Memory is already compact enough."
        compacted = items[:1] + items[-4:]
        await self._session.clear_session()
        await self._session.add_items(compacted)
        return f"Memory compacted. Reduced from {before} to {len(compacted)} items."

    async def delete(self) -> str:
        await self._session.clear_session()
        return "Memory deleted successfully."
