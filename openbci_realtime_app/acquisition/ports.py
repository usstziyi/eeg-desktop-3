import sys


def list_serial_ports() -> list[str]:
    if sys.platform.startswith("win"):
        return _list_windows_ports()
    elif sys.platform.startswith("linux"):
        return _list_linux_ports()
    elif sys.platform.startswith("darwin"):
        return _list_macos_ports()
    return []


def _list_windows_ports() -> list[str]:
    ports = []
    for i in range(1, 33):
        port = f"COM{i}"
        try:
            import serial
            s = serial.Serial(port)
            s.close()
            ports.append(port)
        except (ImportError, OSError):
            pass
    return ports


def _list_linux_ports() -> list[str]:
    import glob
    return glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")


def _list_macos_ports() -> list[str]:
    import glob
    return glob.glob("/dev/cu.*")
