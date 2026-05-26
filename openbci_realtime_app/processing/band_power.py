import numpy as np


def _band_power(
    freqs: np.ndarray, psd: np.ndarray, low: float, high: float
) -> float:
    mask = (freqs >= low) & (freqs <= high)
    if not np.any(mask):
        return 0.0
    return float(np.trapezoid(psd[mask], freqs[mask]))


def compute_band_powers(
    psd_values: np.ndarray,
    freqs: np.ndarray,
    band_defs: dict[str, tuple[float, float]],
) -> list[dict[str, float]]:
    total_power = np.trapezoid(psd_values, freqs, axis=1)
    result: list[dict[str, float]] = []
    for ch_psd, total in zip(psd_values, total_power):
        ch_powers: dict[str, float] = {}
        for band_name, (low, high) in band_defs.items():
            abs_power = _band_power(freqs, ch_psd, low, high)
            ch_powers[band_name] = float(abs_power / total) if total > 0 else 0.0
        result.append(ch_powers)
    return result
