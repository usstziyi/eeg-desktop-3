from dataclasses import dataclass, field

import numpy as np
from scipy import signal

_WINDOW_MAP = {
    "Hann": "hann",
    "Blackman": "blackman",
    "Bartlett": "bartlett",
    "Rectangular": "boxcar",
}


@dataclass
class PSDResult:
    freqs: np.ndarray
    psd: np.ndarray
    band_powers: list = field(default_factory=list)


class PSDAnalyzer:
    def __init__(
        self,
        sampling_rate: float = 250.0,
        window_type: str = "Hann",
        spectrum_window: float = 4.0,
        overlap_ratio: float = 50.0,
    ):
        self._fs = sampling_rate
        self._window_type = window_type
        self._spectrum_window = spectrum_window
        self._overlap_ratio = overlap_ratio

    def update_config(
        self,
        sampling_rate: float | None = None,
        window_type: str | None = None,
        spectrum_window: float | None = None,
        overlap_ratio: float | None = None,
    ) -> None:
        if sampling_rate is not None:
            self._fs = sampling_rate
        if window_type is not None:
            self._window_type = window_type
        if spectrum_window is not None:
            self._spectrum_window = spectrum_window
        if overlap_ratio is not None:
            self._overlap_ratio = overlap_ratio

    def compute(
        self,
        eeg_data: np.ndarray,
        band_defs: dict[str, tuple[float, float]] | None = None,
    ) -> PSDResult:
        freqs, psd = self._welch(eeg_data)

        band_powers: list = []
        if band_defs is not None:
            band_powers = self._compute_band_powers(psd, freqs, band_defs)

        return PSDResult(freqs=freqs, psd=psd, band_powers=band_powers)

    def _welch(self, data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        nperseg = int(self._spectrum_window * self._fs)
        if nperseg < 64:
            nperseg = 64
        if nperseg > data.shape[1]:
            nperseg = data.shape[1]
        noverlap = int(nperseg * self._overlap_ratio / 100.0)

        win_name = _WINDOW_MAP.get(self._window_type, "hann")

        psd_list: list[np.ndarray] = []
        freqs: np.ndarray | None = None
        for ch_data in data:
            f, pxx = signal.welch(
                ch_data,
                fs=self._fs,
                window=win_name,
                nperseg=nperseg,
                noverlap=noverlap,
            )
            if freqs is None:
                freqs = f
            psd_list.append(pxx)

        return freqs, np.array(psd_list)

    @staticmethod
    def _compute_band_powers(
        psd: np.ndarray,
        freqs: np.ndarray,
        band_defs: dict[str, tuple[float, float]],
    ) -> list[dict[str, float]]:
        total_power = np.trapezoid(psd, freqs, axis=1)
        result: list[dict[str, float]] = []
        for ch_psd, total in zip(psd, total_power):
            ch_powers: dict[str, float] = {}
            for band_name, (low, high) in band_defs.items():
                mask = (freqs >= low) & (freqs <= high)
                if not np.any(mask):
                    ch_powers[band_name] = 0.0
                    continue
                abs_power = float(np.trapezoid(ch_psd[mask], freqs[mask]))
                ch_powers[band_name] = float(abs_power / total) if total > 0 else 0.0
            result.append(ch_powers)
        return result
