from __future__ import annotations

from serial.tools.list_ports import comports


def list_serial_ports() -> list[str]:
    return sorted(p.device for p in comports())
