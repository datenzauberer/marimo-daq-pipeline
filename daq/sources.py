"""DAQ source descriptions and Pico/RP2040 port discovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from serial.tools import list_ports


RASPBERRY_PI_USB_VID = 0x2E8A
MICROPYTHON_RP2_USB_PID = 0x0005


class SourceKind(Enum):
    PICO = "pico"
    SIMULATOR = "simulator"


@dataclass(frozen=True)
class DAQSource:
    kind: SourceKind
    label: str
    port: str | None = None

    @property
    def source_id(self) -> str:
        return f"{self.kind.value}:{self.port or 'internal'}"


def _is_pico_or_rp2040(port: object) -> bool:
    identity = " ".join(
        str(getattr(port, attribute, None) or "")
        for attribute in ("description", "manufacturer", "product", "hwid")
    ).lower()
    is_micropython_rp2 = (
        getattr(port, "vid", None) == RASPBERRY_PI_USB_VID
        and getattr(port, "pid", None) == MICROPYTHON_RP2_USB_PID
    )
    return is_micropython_rp2 or "rp2040" in identity


def scan_daq_sources() -> list[DAQSource]:
    ports = sorted(
        (port for port in list_ports.comports() if _is_pico_or_rp2040(port)),
        key=lambda port: port.device,
    )
    sources = [
        DAQSource(
            kind=SourceKind.PICO,
            label=f"Pico/RP2040 DAQ — {port.device}",
            port=port.device,
        )
        for port in ports
    ]
    sources.append(
        DAQSource(
            kind=SourceKind.SIMULATOR,
            label="Software-Simulator (Mock)",
        )
    )
    return sources
