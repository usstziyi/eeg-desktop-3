from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from .realtime_filters import RealtimeFilter
from .spectrum import compute_psd_welch
from .band_power import compute_band_powers


BAND_DEFS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}


@dataclass(frozen=True)
class ProcessingConfig:
    # 去趋势
    detrend: bool = True
    # 滤波
    bp_low_hz: float = 0.1
    bp_high_hz: float = 45.0
    notch_hz: float = 50.0
    sampling_rate: float = 250.0
    # psd
    window_type: str = "Hann"
    spectrum_window: float = 4.0
    overlap_ratio: float = 50


@dataclass(frozen=True)
class ProcessingResult:
    eeg_processed: np.ndarray
    psd_freqs: np.ndarray
    psd_values: np.ndarray
    band_powers: list = field(default_factory=list)


class ProcessingWorker(QObject):
    processed_ready = Signal(object)
    _trigger = Signal(object)

    def __init__(self, parent: QObject | None = None, n_channels: int = 8):
        super().__init__(parent)
        self._config = ProcessingConfig()
        self._n_channels = n_channels
        self._filter = RealtimeFilter(
            fs=self._config.sampling_rate,
            bp_low_hz=self._config.bp_low_hz,
            bp_high_hz=self._config.bp_high_hz,
            notch_hz=self._config.notch_hz,
            n_channels=n_channels,
        )
        self._trigger.connect(self._do_process)

    def update_config(self, config: ProcessingConfig) -> None:
        old = self._config
        self._config = config
        if (old.bp_low_hz != config.bp_low_hz
            or old.bp_high_hz != config.bp_high_hz
            or old.notch_hz != config.notch_hz
            or old.sampling_rate != config.sampling_rate):
            self._filter = RealtimeFilter(
                fs=config.sampling_rate,
                bp_low_hz=config.bp_low_hz,
                bp_high_hz=config.bp_high_hz,
                notch_hz=config.notch_hz,
                n_channels=self._n_channels,
            )

# """
#     主线程 (_on_timer_tick)              工作线程 (QThread 事件循环)
#     ──────────────────────               ──────────────────────────
#     process(data)                      
#         │                                
#         _trigger.emit(data)  ──── QueuedConnection ────→ _do_process(data)
#         │                                                    │
#     立即返回 ❌不阻塞                                    真正干活
# """
    def process(self, eeg_data: np.ndarray) -> None:
        self._trigger.emit(eeg_data.copy())



    """
    耗时操作都在这里
    1.去趋势
    2.滤波
    3.计算psd
    4.计算band_power
    """
    @Slot(object)
    def _do_process(self, eeg_data: np.ndarray) -> None:
        config = self._config

        if config.detrend:
            eeg_data = eeg_data - np.mean(eeg_data, axis=1, keepdims=True)

        filtered = self._filter.apply(eeg_data)

        # freqs, psd = compute_psd_welch(
        #     filtered,
        #     fs=config.sampling_rate,
        #     window_type=config.window_type,
        #     window_seconds=config.spectrum_window,
        #     overlap_ratio=config.overlap_ratio,
        # )

        # band_powers = compute_band_powers(psd, freqs, BAND_DEFS)

        result = ProcessingResult(
            eeg_processed=filtered,
            psd_freqs=[],
            psd_values=[],
            band_powers=[],
        )
        self.processed_ready.emit(result)
