"""Pure-Python, in-memory implementation of the DAQ reader."""

from __future__ import annotations

import threading
import time

from .base import DAQReader


class SimulatorDAQReader(DAQReader):
    """Generate monotonically increasing samples at a fixed interval."""

    def __init__(
        self,
        interval_s: float = 0.010,
        max_samples: int = 10_000,
    ):
        super().__init__(max_samples=max_samples)
        self.interval_s = interval_s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._control_lock = threading.RLock()
        self._set_state(mode="simulation", status="Software-Simulator ausgewählt")

    def start(self) -> str:
        with self._control_lock:
            self.stop()
            self.clear()
            self._stop_event.clear()
            self._set_state(
                running=True,
                mode="simulation",
                status="Simulations-Modus aktiv",
            )
            self._thread = threading.Thread(
                target=self._run,
                name="daq-software-simulator",
                daemon=True,
            )
            self._thread.start()
            return "Software-Simulator mit 100 Hz gestartet."

    def _run(self) -> None:
        value = 0
        next_tick = time.monotonic()
        while not self._stop_event.is_set():
            self._append(time.monotonic_ns() // 1_000_000, value)
            value += 1
            next_tick += self.interval_s
            delay = max(0.0, next_tick - time.monotonic())
            if self._stop_event.wait(delay):
                break

    def stop(self) -> str:
        with self._control_lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout=0.5)
            self._set_state(
                running=False,
                mode="simulation",
                status="Simulations-Modus aktiv (gestoppt)",
            )
            return "Simulator-Messung gestoppt."

    def close(self) -> None:
        self.stop()
