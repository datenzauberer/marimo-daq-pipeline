"""Lifecycle controller that selects exactly one DAQ backend."""

from __future__ import annotations

import threading

from .base import DAQReader, Sample
from .pico import PicoDAQReader
from .simulator import SimulatorDAQReader
from .sources import DAQSource, SourceKind


def _create_reader(source: DAQSource, max_samples: int) -> DAQReader:
    if source.kind is SourceKind.PICO:
        if source.port is None:
            raise ValueError("Für die Pico-Quelle fehlt der serielle Port.")
        return PicoDAQReader(port=source.port, max_samples=max_samples)
    if source.kind is SourceKind.SIMULATOR:
        return SimulatorDAQReader(interval_s=0.010, max_samples=max_samples)
    raise ValueError(f"Unbekannte DAQ-Quelle: {source.kind}")


class DAQController:
    """Own the backend selected by the UI and coordinate its lifecycle."""

    def __init__(self, max_samples: int = 10_000):
        self._max_samples = max_samples
        self._reader: DAQReader | None = None
        self._source: DAQSource | None = None
        self._lock = threading.RLock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._reader.is_running if self._reader is not None else False

    def select_source(self, source: DAQSource) -> str:
        with self._lock:
            if source == self._source and self._reader is not None:
                return f"Quelle ausgewählt: {source.label}"
            if self._reader is not None:
                self._reader.close()
            self._reader = _create_reader(source, self._max_samples)
            self._source = source
            return f"Quelle ausgewählt: {source.label}"

    def start(self) -> str:
        with self._lock:
            if self._reader is None:
                raise RuntimeError("Keine DAQ-Quelle ausgewählt.")
            return self._reader.start()

    def stop(self) -> str:
        with self._lock:
            if self._reader is None:
                raise RuntimeError("Keine DAQ-Quelle ausgewählt.")
            return self._reader.stop()

    def snapshot(self) -> list[Sample]:
        with self._lock:
            return self._reader.snapshot() if self._reader is not None else []

    def status_snapshot(self) -> dict[str, object]:
        with self._lock:
            if self._reader is None:
                return {
                    "mode": "idle",
                    "text": "Keine DAQ-Quelle ausgewählt",
                    "samples": 0,
                    "running": False,
                    "error": None,
                }
            return self._reader.status_snapshot()

    def close(self) -> None:
        with self._lock:
            if self._reader is not None:
                self._reader.close()
            self._reader = None
            self._source = None
