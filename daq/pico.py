"""USB-CDC/PySerial implementation of the DAQ reader."""

from __future__ import annotations

import threading
import time

import serial

from .base import DAQReader


class PicoDAQReader(DAQReader):
    """Acquire samples only from one selected Pico serial port."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115_200,
        max_samples: int = 10_000,
    ):
        super().__init__(max_samples=max_samples)
        self.port = port
        self.baudrate = baudrate
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._control_lock = threading.RLock()
        self._set_state(mode="hardware", status=f"Pico ausgewählt auf {port}")

    def _close_serial(self) -> None:
        connection = self._serial
        self._serial = None
        if connection is not None:
            try:
                connection.close()
            except (serial.SerialException, OSError):
                pass

    def start(self) -> str:
        with self._control_lock:
            self.stop()
            self.clear()
            try:
                connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=0.1,
                    write_timeout=1.0,
                )
                connection.reset_input_buffer()
                connection.write(b"START\n")
                connection.flush()
            except (serial.SerialException, OSError, ValueError) as exc:
                if "connection" in locals():
                    connection.close()
                message = f"Pico-Verbindung auf {self.port} fehlgeschlagen: {exc}"
                self._set_state(
                    running=False,
                    mode="error",
                    status="Pico-Verbindungsfehler",
                    error=message,
                )
                raise ConnectionError(message) from exc

            self._serial = connection
            self._stop_event.clear()
            self._set_state(
                running=True,
                mode="hardware",
                status=f"Pico verbunden auf {self.port}",
            )
            self._thread = threading.Thread(
                target=self._read_loop,
                name="daq-pico-reader",
                daemon=True,
            )
            self._thread.start()
            return f"START an {self.port} gesendet."

    def _read_loop(self) -> None:
        first_sample_deadline = time.monotonic() + 1.0
        received_sample = False
        try:
            while not self._stop_event.is_set():
                connection = self._serial
                if connection is None:
                    raise serial.SerialException("Serielle Verbindung wurde geschlossen")
                raw_line = connection.readline()
                if raw_line:
                    try:
                        fields = raw_line.decode("ascii").strip().split(",")
                        if len(fields) == 2:
                            self._append(fields[0], fields[1])
                            received_sample = True
                    except (UnicodeDecodeError, ValueError):
                        pass

                if not received_sample and time.monotonic() >= first_sample_deadline:
                    raise serial.SerialException(
                        "Keine gültigen Pico-Messdaten innerhalb von 1 s"
                    )
        except (serial.SerialException, OSError) as exc:
            if not self._stop_event.is_set():
                message = f"Serielle Pico-Verbindung verloren: {exc}"
                self._set_state(
                    running=False,
                    mode="error",
                    status="Pico-Verbindungsfehler",
                    error=message,
                )
                self._close_serial()

    def stop(self) -> str:
        with self._control_lock:
            self._stop_event.set()
            connection = self._serial
            if connection is not None and connection.is_open:
                try:
                    connection.write(b"STOP\n")
                    connection.flush()
                except (serial.SerialException, OSError):
                    pass

            thread = self._thread
            self._thread = None
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout=0.5)
            self._close_serial()

            if self.status_snapshot()["mode"] != "error":
                self._set_state(
                    running=False,
                    mode="hardware",
                    status=f"Pico auf {self.port} (gestoppt)",
                )
            return "Pico-Messung gestoppt."

    def close(self) -> None:
        self.stop()
