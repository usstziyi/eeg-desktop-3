import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from .types import FilterConfig, ProcessedData
from .filters import apply_filter_chain
from .spectrum import compute_psd_welch
from .band_power import compute_band_powers


class ProcessingWorker(QObject):
    processed_ready = Signal(object)
    _trigger = Signal(object, float)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._filter_config = FilterConfig()
        self._psd_window_seconds = 4.0
        self._welch_overlap = 0.5
        self._trigger.connect(self._do_process)

    def update_config(
        self,
        filter_config: FilterConfig,
        psd_window_seconds: float,
        welch_overlap: float,
    ) -> None:
        self._filter_config = filter_config
        self._psd_window_seconds = psd_window_seconds
        self._welch_overlap = welch_overlap

    def process(self, raw_eeg: np.ndarray, sampling_rate: float) -> None:
        # 主线程发射信号，自动选择 QueuedConnection，发给子线程
        self._trigger.emit(raw_eeg, sampling_rate)

    @Slot(object, float)
    def _do_process(self, raw_eeg: np.ndarray, sampling_rate: float) -> None:
        if raw_eeg.size == 0:
            return
        filtered = apply_filter_chain(raw_eeg.copy(), sampling_rate, self._filter_config)
        freqs, psd_vals = compute_psd_welch(
            filtered, sampling_rate, self._psd_window_seconds, self._welch_overlap
        )
        band_powers = compute_band_powers(filtered, sampling_rate)
        result = ProcessedData(
            filtered_eeg=filtered,
            psd_freqs=freqs,
            psd_values=psd_vals,
            band_powers=band_powers,
        )
        self.processed_ready.emit(result)
