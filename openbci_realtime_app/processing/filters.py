import numpy as np
from scipy import signal


def _design_bandpass(low: float, high: float, fs: float, order: int = 4) -> np.ndarray:
    sos = signal.butter(
        order,
        [low, high],
        btype="bandpass",
        fs=fs,
        output="sos",
    )
    return sos


def _design_notch(freq: float, fs: float, q: float = 30.0) -> np.ndarray:
    # 设计陷波滤波器（IIR陷波器），返回传递函数形式的分子分母系数
    sos = signal.iirnotch(freq, q, fs=fs)
    # 将传递函数形式转换为二阶节(SOS)形式，便于数值稳定性处理
    return signal.tf2sos(*sos)


def apply_filter_chain(
    data: np.ndarray,
    fs: float,  # 采样频率
    bp_low_hz: float = 0.1,
    bp_high_hz: float = 45.0,
    notch_hz: float = 50.0,
    bp_order: int = 4,
    notch_q: float = 30.0,
) -> np.ndarray:
    n_samples = data.shape[1]
    sos_bp = _design_bandpass(bp_low_hz, bp_high_hz, fs, order=bp_order)

    # padlen = 3 * (2 * n_sections + 1), 带通 4 阶产生 4 个 SOS 节 → padlen=27
    min_len = 3 * (2 * sos_bp.shape[0] + 1) + 1
    if n_samples < min_len:
        return data

    filtered = signal.sosfiltfilt(sos_bp, data, axis=1)

    if notch_hz > 0:
        sos_notch = _design_notch(notch_hz, fs, q=notch_q)
        min_len_n = 3 * (2 * sos_notch.shape[0] + 1) + 1
        if filtered.shape[1] >= min_len_n:
            filtered = signal.sosfiltfilt(sos_notch, filtered, axis=1)

    return filtered
