import numpy as np
from scipy import signal


class RealtimeFilter:
    def __init__(
        self,
        fs: float,
        bp_low_hz: float = 0.1,
        bp_high_hz: float = 45.0,
        notch_hz: float = 50.0,
        bp_order: int = 4,
        notch_q: float = 30.0,
        n_channels: int = 8,
    ):
        self._fs = fs
        self._n_channels = n_channels

        self._sos_bp = _design_bandpass(bp_low_hz, bp_high_hz, fs, bp_order)
        self._zi_bp = _init_zi(self._sos_bp, n_channels)

        if notch_hz > 0:
            self._sos_notch = _design_notch(notch_hz, fs, notch_q)
            self._zi_notch = _init_zi(self._sos_notch, n_channels)
        else:
            self._sos_notch = None
            self._zi_notch = None

    def reset(self) -> None:
        self._zi_bp = _init_zi(self._sos_bp, self._n_channels)
        if self._sos_notch is not None:
            self._zi_notch = _init_zi(self._sos_notch, self._n_channels)

    def apply(self, data: np.ndarray) -> np.ndarray:
        filtered, self._zi_bp = signal.sosfilt(
            self._sos_bp, data, axis=1, zi=self._zi_bp
        )
        if self._sos_notch is not None:
            filtered, self._zi_notch = signal.sosfilt(
                self._sos_notch, filtered, axis=1, zi=self._zi_notch
            )
        return filtered


def _init_zi(sos: np.ndarray, n_channels: int) -> np.ndarray:
    zi_2d = signal.sosfilt_zi(sos)
    return np.tile(zi_2d[:, np.newaxis, :], (1, n_channels, 1))


def _design_bandpass(
    low: float, high: float, fs: float, order: int = 4
) -> np.ndarray:
    return signal.butter(order, [low, high], btype="bandpass", fs=fs, output="sos")


def _design_notch(freq: float, fs: float, q: float = 30.0) -> np.ndarray:
    b, a = signal.iirnotch(freq, q, fs=fs)
    return signal.tf2sos(b, a)
