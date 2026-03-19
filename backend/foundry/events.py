from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def on(self, event_name: str, handler: EventHandler) -> None:
        async with self._lock:
            self._handlers[event_name].append(handler)

    async def emit(self, event_name: str, data: dict[str, Any]) -> None:
        async with self._lock:
            handlers = list(self._handlers.get(event_name, []))
        if handlers:
            await asyncio.gather(*(handler(data) for handler in handlers), return_exceptions=False)


_event_bus = EventBus()


async def on(event_name: str, handler: EventHandler) -> None:
    await _event_bus.on(event_name, handler)


async def emit(event_name: str, data: dict[str, Any]) -> None:
    await _event_bus.emit(event_name, data)
