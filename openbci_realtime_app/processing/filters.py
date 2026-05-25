import numpy as np
from brainflow.data_filter import (
    DataFilter,
    DetrendOperations,
    FilterTypes,
    NoiseTypes,
)
from .types import FilterConfig


def apply_filter_chain(
    data: np.ndarray, sampling_rate: float, config: FilterConfig
) -> np.ndarray:
    if data.size == 0:
        return data
    sampling_rate_int = int(sampling_rate)
    result = data.astype(np.float64).copy()
    for ch_idx in range(result.shape[0]):
        DataFilter.detrend(result[ch_idx], DetrendOperations.CONSTANT.value)
        DataFilter.perform_bandpass(
            result[ch_idx],
            sampling_rate_int,
            config.bandpass_low,
            config.bandpass_high,
            4,
            FilterTypes.BUTTERWORTH.value,
            0.0,
        )
        if config.notch > 0:
            DataFilter.remove_environmental_noise(
                result[ch_idx],
                sampling_rate_int,
                NoiseTypes.FIFTY.value
                if config.notch == 50.0
                else NoiseTypes.SIXTY.value,
            )
    return result
