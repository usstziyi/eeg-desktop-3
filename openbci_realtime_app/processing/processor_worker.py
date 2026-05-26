from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

# from .filters import apply_filter_chain
# from .spectrum import compute_psd_welch
# from .band_power import compute_band_powers



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
    # psd
    window_type: str = "Hamming"
    spectrum_window: float = 4.0
    overlap_ratio: float = 50


@dataclass(frozen=True)
class ProcessingResult:
    eeg_processed: np.ndarray
    psd_freqs: np.ndarray
    psd_values: np.ndarray
    band_powers: np.ndarray


class ProcessingWorker(QObject):
    processed_ready = Signal(object)
    _trigger = Signal(object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._config = ProcessingConfig()
        self._trigger.connect(self._do_process)

    def update_config(self, config: ProcessingConfig) -> None:
        self._config = config

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
        config = self._config   # 一次原子读取，锁定快照
        # TODO
        # 1.去趋势
        if config.detrend:
            eeg_data -= np.mean(eeg_data, axis=1, keepdims=True)

        # 2.滤波
        
        # 3.计算psd
        # 4.计算band_power





        result = ProcessingResult(
            eeg_processed=eeg_data,
            psd_freqs=[],
            psd_values=[],
            band_powers=[],
        )
        self.processed_ready.emit(result)
