"""Common interface and thread-safe sample buffer for DAQ backends."""

from __future__ import annotations

import collections
import threading
from abc import ABC, abstractmethod


Sample = tuple[int, int]


class DAQReader(ABC):
    """Abstract DAQ backend with a bounded, thread-safe sample buffer."""

    def __init__(self, max_samples: int = 10_000):
        self._samples: collections.deque[Sample] = collections.deque(
            maxlen=max_samples
        )
        self._samples_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._is_running = False
        self._mode = "idle"
        self._status = "DAQ-Quelle ausgewählt"
        self._last_error: str | None = None

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return self._is_running

    def _set_state(
        self,
        *,
        running: bool | None = None,
        mode: str | None = None,
        status: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._state_lock:
            if running is not None:
                self._is_running = running
            if mode is not None:
                self._mode = mode
            if status is not None:
                self._status = status
            self._last_error = error

    def status_snapshot(self) -> dict[str, object]:
        with self._state_lock:
            state = {
                "mode": self._mode,
                "text": self._status,
                "running": self._is_running,
                "error": self._last_error,
            }
        with self._samples_lock:
            state["samples"] = len(self._samples)
        return state

    def clear(self) -> None:
        with self._samples_lock:
            self._samples.clear()

    def snapshot(self) -> list[Sample]:
        with self._samples_lock:
            return list(self._samples)

    def _append(self, timestamp_ms: int | str, value: int | str) -> None:
        with self._samples_lock:
            self._samples.append((int(timestamp_ms), int(value)))

    @abstractmethod
    def start(self) -> str:
        """Start acquisition and return a user-facing status message."""

    @abstractmethod
    def stop(self) -> str:
        """Stop acquisition and return a user-facing status message."""

    @abstractmethod
    def close(self) -> None:
        """Release threads and external resources."""
