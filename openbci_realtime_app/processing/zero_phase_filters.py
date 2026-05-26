import numpy as np
from scipy import signal


class ZeroPhaseSOSFilter:
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
        self._bp_low_hz = bp_low_hz
        self._bp_high_hz = bp_high_hz
        self._bp_order = bp_order
        self._notch_hz = notch_hz
        self._notch_q = notch_q

        self._design_filters()

    def reset(self) -> None:
        pass

    def update_config(
        self,
        fs: float | None = None,
        bp_low_hz: float | None = None,
        bp_high_hz: float | None = None,
        notch_hz: float | None = None,
        bp_order: int | None = None,
        notch_q: float | None = None,
        n_channels: int | None = None,
    ) -> None:
        if fs is not None:
            self._fs = fs
        if n_channels is not None:
            self._n_channels = n_channels

        low = bp_low_hz if bp_low_hz is not None else self._bp_low_hz
        high = bp_high_hz if bp_high_hz is not None else self._bp_high_hz
        order = bp_order if bp_order is not None else self._bp_order
        nhz = notch_hz if notch_hz is not None else self._notch_hz
        nq = notch_q if notch_q is not None else self._notch_q

        self._bp_low_hz = low
        self._bp_high_hz = high
        self._bp_order = order
        self._notch_hz = nhz
        self._notch_q = nq


        self._design_filters()

    def _design_filters(self) -> None:
        self._sos_bp = _design_bandpass(
            self._bp_low_hz, self._bp_high_hz, self._fs, self._bp_order
        )
        self._min_len_bp = 3 * (2 * self._sos_bp.shape[0] + 1) + 1 # 28

        if self._notch_hz > 0:
            self._sos_notch = _design_notch(self._notch_hz, self._fs, self._notch_q)
            self._min_len_notch = 3 * (2 * self._sos_notch.shape[0] + 1) + 1 # 10
        else:
            self._sos_notch = None
            self._min_len_notch = 0

    def apply(self, data: np.ndarray) -> np.ndarray:
        n_samples = data.shape[1]
        if n_samples < self._min_len_bp:
            return data

        filtered = signal.sosfiltfilt(self._sos_bp, data, axis=1)

        if self._sos_notch is not None and filtered.shape[1] >= self._min_len_notch:
            filtered = signal.sosfiltfilt(self._sos_notch, filtered, axis=1)

        return filtered


def _design_bandpass(
    low: float, high: float, fs: float, order: int = 4
) -> np.ndarray:
    return signal.butter(order, [low, high], btype="bandpass", fs=fs, output="sos")


def _design_notch(freq: float, fs: float, q: float = 30.0) -> np.ndarray:
    b, a = signal.iirnotch(freq, q, fs=fs)
    return signal.tf2sos(b, a)
