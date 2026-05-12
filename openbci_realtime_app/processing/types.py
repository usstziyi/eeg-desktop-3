from dataclasses import dataclass, field

import numpy as np

BAND_DEFS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}


@dataclass
class FilterConfig:
    bandpass_low: float = 1.0
    bandpass_high: float = 45.0
    notch: float = 50.0
    sampling_rate: float = 250.0


@dataclass
class ProcessedData:
    filtered_eeg: np.ndarray = field(default_factory=lambda: np.array([]))
    psd_freqs: np.ndarray = field(default_factory=lambda: np.array([]))
    psd_values: np.ndarray = field(default_factory=lambda: np.array([]))
    band_powers: dict = field(default_factory=dict)
