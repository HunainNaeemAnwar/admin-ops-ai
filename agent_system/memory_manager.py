from datetime import datetime, timedelta
from pathlib import Path
from agents import SQLiteSession

MEMORY_DIR = Path("data/agent_memory")
MEMORY_DB = str(MEMORY_DIR / "agent_memory.db")


class ConversationMemory:
    MAX_TOKENS_ESTIMATE = 6000
    AUTO_COMPACT_KEEP = 8

    @staticmethod
    def load_from_db(session_id: str) -> list:
        from tools.database import load_chat_messages
        return load_chat_messages(session_id)

    @staticmethod
    def save_to_db(session_id: str, messages: list):
        from tools.database import save_chat_messages
        save_chat_messages(session_id, messages)

    @staticmethod
    def delete_from_db(session_id: str):
        from tools.database import delete_chat_messages
        delete_chat_messages(session_id)

    def __init__(self, session_id: str):
        self.session_id = session_id
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._session = SQLiteSession(session_id, MEMORY_DB)

    @property
    def session(self) -> SQLiteSession:
        return self._session

    async def _estimate_tokens(self, items) -> int:
        return sum(len(str(item)) for item in items) // 3

    async def turn_count(self) -> int:
        items = await self._session.get_items()
        return len(items)

    async def _clean_dangling(self, items: list) -> list:
        """Remove tool messages that have no matching tool_call in the preceding assistant message."""
        if not items:
            return items
        clean = [items[0]]
        i = 1
        while i < len(items):
            item = items[i]
            if isinstance(item, dict) and item.get("role") == "tool":
                prev = clean[-1] if clean else None
                tcid = item.get("tool_call_id") or item.get("id")
                if (not isinstance(prev, dict)) or prev.get("role") != "assistant" or not prev.get("tool_calls"):
                    i += 1
                    continue
                tcall_ids = {tc.get("id") for tc in (prev.get("tool_calls") or [])}
                if tcid not in tcall_ids:
                    i += 1
                    continue
            clean.append(item)
            i += 1
        return clean

    async def compact_if_needed(self) -> str:
        items = await self._session.get_items()
        estimated = await self._estimate_tokens(items)
        if estimated < self.MAX_TOKENS_ESTIMATE:
            return f"Memory OK (~{estimated} tokens)"
        before = len(items)
        keep_count = min(self.AUTO_COMPACT_KEEP, len(items) - 1)
        compacted = items[:1] + items[-keep_count:]
        clean = await self._clean_dangling(compacted)
        await self._session.clear_session()
        await self._session.add_items(clean)
        return f"Memory compacted: {before} -> {len(clean)} items (~{estimated} tokens)"

    async def compact(self) -> str:
        return await self.compact_if_needed()

    async def cleanup(self) -> str:
        """Remove dangling tool messages from memory. Safe to call before every turn."""
        items = await self._session.get_items()
        before = len(items)
        clean = await self._clean_dangling(items)
        if len(clean) < before:
            await self._session.clear_session()
            await self._session.add_items(clean)
            return f"Cleaned {before - len(clean)} dangling message(s)"
        return "No cleanup needed"

    async def delete(self) -> str:
        await self._session.clear_session()
        return "Memory deleted successfully."
