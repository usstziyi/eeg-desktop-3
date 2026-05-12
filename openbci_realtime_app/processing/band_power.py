import numpy as np
from brainflow.data_filter import DataFilter


def compute_band_powers(
    data: np.ndarray,
    sampling_rate: float,
    fft_size: int | None = None,
) -> list[dict]:
    if data.size == 0:
        return []
    nfft = fft_size or DataFilter.get_nearest_power_of_two(int(sampling_rate))
    results = []
    for ch_idx in range(data.shape[0]):
        channel_data = data[ch_idx].astype(np.float64)
        (delta, theta, alpha, beta, gamma) = DataFilter.get_band_power(
            channel_data,
            int(sampling_rate),
            nfft,
        )
        results.append({
            "delta": delta,
            "theta": theta,
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
        })
    return results
