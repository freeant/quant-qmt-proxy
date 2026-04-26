from __future__ import annotations

import queue
import threading
import uuid
from collections import defaultdict
from typing import Any, Callable, Iterator

from app.utils.logger import logger


class TradingEventStream(Iterator[dict[str, Any]]):
    def __init__(
        self,
        hub: "TradingEventHub",
        session_id: str,
        consumer_id: str,
        consumer_queue: queue.Queue,
        stop_checker: Callable[[], bool] | None = None,
    ):
        self._hub = hub
        self._session_id = session_id
        self._consumer_id = consumer_id
        self._consumer_queue = consumer_queue
        self._stop_checker = stop_checker
        self._closed = False

    def __iter__(self) -> "TradingEventStream":
        return self

    def __next__(self) -> dict[str, Any]:
        while self._stop_checker is None or self._stop_checker():
            try:
                event = self._consumer_queue.get(timeout=1.0)
                if event is self._hub.STREAM_CLOSED:
                    self.close()
                    raise StopIteration
                return event
            except queue.Empty:
                continue
        self.close()
        raise StopIteration

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._hub.unregister(self._session_id, self._consumer_id)


class TradingEventHub:
    STREAM_CLOSED = object()

    def __init__(self, maxsize: int = 1024):
        self.maxsize = maxsize
        self._lock = threading.RLock()
        self._consumers: dict[str, dict[str, queue.Queue]] = defaultdict(dict)
        self._drop_counts: dict[str, dict[str, int]] = defaultdict(dict)

    def register(self, session_id: str) -> tuple[str, queue.Queue]:
        consumer_id = uuid.uuid4().hex
        consumer_queue: queue.Queue = queue.Queue(maxsize=self.maxsize)
        with self._lock:
            self._consumers[session_id][consumer_id] = consumer_queue
            self._drop_counts[session_id][consumer_id] = 0
        return consumer_id, consumer_queue

    def unregister(self, session_id: str, consumer_id: str) -> None:
        with self._lock:
            consumers = self._consumers.get(session_id)
            drop_counts = self._drop_counts.get(session_id)
            if not consumers:
                return
            consumers.pop(consumer_id, None)
            if drop_counts:
                drop_counts.pop(consumer_id, None)
            if not consumers:
                self._consumers.pop(session_id, None)
                self._drop_counts.pop(session_id, None)

    def publish(self, session_id: str, event: Any) -> None:
        with self._lock:
            consumers = list(self._consumers.get(session_id, {}).items())

        for consumer_id, consumer_queue in consumers:
            try:
                consumer_queue.put_nowait(event)
            except queue.Full:
                try:
                    consumer_queue.get_nowait()
                except queue.Empty:
                    pass
                consumer_queue.put_nowait(event)
                with self._lock:
                    dropped_total = self._drop_counts[session_id].get(consumer_id, 0) + 1
                    self._drop_counts[session_id][consumer_id] = dropped_total
                if dropped_total == 1 or dropped_total % 100 == 0:
                    logger.warning(
                        f"trading event queue overflow: session_id={session_id}, consumer_id={consumer_id}, dropped_total={dropped_total}"
                    )

    def close_session_streams(self, session_id: str) -> None:
        self.publish(session_id, self.STREAM_CLOSED)

    def stream(
        self,
        session_id: str,
        stop_checker: Callable[[], bool] | None = None,
    ) -> TradingEventStream:
        consumer_id, consumer_queue = self.register(session_id)
        return TradingEventStream(
            hub=self,
            session_id=session_id,
            consumer_id=consumer_id,
            consumer_queue=consumer_queue,
            stop_checker=stop_checker,
        )
