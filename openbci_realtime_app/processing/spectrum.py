import numpy as np
from scipy import signal


_WINDOW_MAP = {
    "Hann": "hann",
    "Blackman": "blackman",
    "Bartlett": "bartlett",
    "Rectangular": "boxcar",
}


def compute_psd_welch(
    data: np.ndarray,
    fs: float,
    window_type: str = "Hann",
    window_seconds: float = 4.0,
    overlap_ratio: float = 50.0,
) -> tuple[np.ndarray, np.ndarray]:
    nperseg = int(window_seconds * fs)
    if nperseg < 64:
        nperseg = 64
    if nperseg > data.shape[1]:
        nperseg = data.shape[1]
    noverlap = int(nperseg * overlap_ratio / 100.0)

    win_name = _WINDOW_MAP.get(window_type, "hann")

    psd_list: list[np.ndarray] = []
    freqs: np.ndarray | None = None
    for ch_data in data:
        f, pxx = signal.welch(
            ch_data,
            fs=fs,
            window=win_name,
            nperseg=nperseg,
            noverlap=noverlap,
        )
        if freqs is None:
            freqs = f
        psd_list.append(pxx)

    return freqs, np.array(psd_list)
