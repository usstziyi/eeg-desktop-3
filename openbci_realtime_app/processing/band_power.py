from dataclasses import dataclass

import numpy as np

BAND_DEFS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}


@dataclass
class BandPowerResult:
    band_powers: list


class BandPowerAnalyzer:
    def compute(
        self,
        psd: np.ndarray,
        freqs: np.ndarray,
    ) -> BandPowerResult:
        total_power = np.trapezoid(psd, freqs, axis=1)
        band_powers: list = []
        for ch_psd, total in zip(psd, total_power):
            ch_powers: dict[str, float] = {}
            for band_name, (low, high) in BAND_DEFS.items():
                mask = (freqs >= low) & (freqs <= high)
                if not np.any(mask):
                    ch_powers[band_name] = 0.0
                    continue
                abs_power = float(np.trapezoid(ch_psd[mask], freqs[mask]))
                ch_powers[band_name] = float(abs_power / total) if total > 0 else 0.0
            band_powers.append(ch_powers)
        return BandPowerResult(band_powers=band_powers)
