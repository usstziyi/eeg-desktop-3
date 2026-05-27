from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from .zero_phase_filters import ZeroPhaseSOSFilter
from .causal_sos_filters import CausalSOSFilter
from .causal_sos_steady_filters import CausalSOSSteadyFilter


from .psd import PSDAnalyzer
from .band_power import BandPowerAnalyzer


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
    _config_changed = Signal()

    def __init__(self, parent: QObject | None = None, n_channels: int = 8):
        super().__init__(parent)
        self._config = ProcessingConfig()
        self._n_channels = n_channels
        
        self._filter = ZeroPhaseSOSFilter(
            fs=self._config.sampling_rate,
            bp_low_hz=self._config.bp_low_hz,
            bp_high_hz=self._config.bp_high_hz,
            notch_hz=self._config.notch_hz,
            n_channels=n_channels,
        )
        self._psd_analyzer = PSDAnalyzer(
            sampling_rate=self._config.sampling_rate,
            window_type=self._config.window_type,
            spectrum_window=self._config.spectrum_window,
            overlap_ratio=self._config.overlap_ratio,
        )
        self._band_power_analyzer = BandPowerAnalyzer()
        self._trigger.connect(self._do_process)
        self._config_changed.connect(self._do_update_config)

    def update_config(self, config: ProcessingConfig) -> None:
        self._config = config
        self._config_changed.emit()

    @Slot()
    def _do_update_config(self) -> None:
        config = self._config
        self._filter.update_config(
            fs=config.sampling_rate,
            bp_low_hz=config.bp_low_hz,
            bp_high_hz=config.bp_high_hz,
            notch_hz=config.notch_hz,
        )
        self._psd_analyzer.update_config(
            sampling_rate=config.sampling_rate,
            window_type=config.window_type,
            spectrum_window=config.spectrum_window,
            overlap_ratio=config.overlap_ratio,
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
        if eeg_data.size == 0 or eeg_data.ndim < 2:
            return
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

        psd_result = self._psd_analyzer.compute(filtered)
        # band_power_result = self._band_power_analyzer.compute(
        #     psd_result.psd, psd_result.freqs
        # )

        result = ProcessingResult(
            eeg_processed=filtered,
            psd_freqs=psd_result.freqs,
            psd_values=psd_result.psd,
            # band_powers=band_power_result.band_powers,
        )
        self.processed_ready.emit(result)
