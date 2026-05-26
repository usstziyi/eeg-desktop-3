import numpy as np
from scipy import signal


class CausalSOSSteadyFilter:
    def __init__(
        self,
        fs: float,
        bp_low_hz: float = 0.5,
        bp_high_hz: float = 40.0,
        notch_hz: float = 50.0,
        bp_order: int = 2,
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
        self._zi_bp = None
        self._zi_notch = None

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
        self._sos_bp = signal.butter(
            self._bp_order, [self._bp_low_hz, self._bp_high_hz],
            btype="bandpass", fs=self._fs, output="sos",
        )
        if self._notch_hz > 0:
            b, a = signal.iirnotch(self._notch_hz, self._notch_q, fs=self._fs)
            self._sos_notch = signal.tf2sos(b, a)
        else:
            self._sos_notch = None
        self._zi_bp = None
        self._zi_notch = None

    def apply(self, data: np.ndarray) -> np.ndarray:
        if data.ndim != 2:
            raise ValueError("data must have shape (n_channels, n_samples)")
        if data.shape[0] != self._n_channels:
            raise ValueError("data.shape[0] must equal n_channels")
        x = data
        if self._zi_bp is None:
            self._zi_bp = _make_zi_for_first_sample(self._sos_bp, x[:, 0])
        y, self._zi_bp = signal.sosfilt(
            self._sos_bp,
            x,
            axis=1,
            zi=self._zi_bp,
        )
        if self._sos_notch is not None:
            if self._zi_notch is None:
                self._zi_notch = _make_zi_for_first_sample(self._sos_notch, y[:, 0])
            y, self._zi_notch = signal.sosfilt(
                self._sos_notch,
                y,
                axis=1,
                zi=self._zi_notch,
            )
        return y


def _make_zi_for_first_sample(sos: np.ndarray, x0: np.ndarray) -> np.ndarray:
    zi = signal.sosfilt_zi(sos)
    zi = zi[:, np.newaxis, :]
    zi = np.tile(zi, (1, len(x0), 1))
    return zi
