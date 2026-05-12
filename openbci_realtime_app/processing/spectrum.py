import numpy as np
from brainflow.data_filter import DataFilter, WindowOperations


def compute_psd_welch(
    data: np.ndarray,
    sampling_rate: float,
    window_seconds: float,
    overlap_ratio: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    if data.size == 0 or data.shape[1] < 4:
        return np.array([]), np.array([])
    nfft = DataFilter.get_nearest_power_of_two(int(sampling_rate))
    num_samples = data.shape[1]
    nperseg = min(int(sampling_rate * window_seconds), num_samples)
    if nperseg < 4:
        nperseg = num_samples
    noverlap = int(nperseg * overlap_ratio)
    detrend_type = int(WindowOperations.NO_WINDOW.value)
    psd_all = []
    for ch_idx in range(data.shape[0]):
        channel_data = data[ch_idx].astype(np.float64)
        psd = DataFilter.get_psd_welch(
            channel_data,
            nfft,
            noverlap,
            int(sampling_rate),
            detrend_type,
        )
        psd_all.append(np.array(psd))
    psd_array = np.array(psd_all)
    freqs = np.linspace(0, sampling_rate / 2, psd_array.shape[1])
    return freqs, psd_array
