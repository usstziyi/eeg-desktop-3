from dataclasses import dataclass

import numpy as np
from scipy import signal

_WINDOW_MAP = {
    "Hann": "hann",           # 汉宁窗，余弦窗的一种，主瓣较窄，旁瓣衰减较快
    "Hamming": "hamming",     # 汉明窗，改进的余弦窗，旁瓣电平更低
    "Blackman": "blackman",   # 布莱克曼窗，二阶余弦窗，旁瓣抑制更好但主瓣更宽
    "Bartlett": "bartlett",   # 巴特利特窗，三角窗，计算简单
    "Rectangular": "boxcar",  # 矩形窗，无衰减，频谱泄漏最大但频率分辨率最高
}


@dataclass
class PSDResult:
    freqs: np.ndarray
    psd: np.ndarray


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

    def compute(self, eeg_data: np.ndarray) -> PSDResult:
        freqs, psd = self._welch(eeg_data)
        return PSDResult(freqs=freqs, psd=psd)

    def _welch(self, data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        nperseg = int(self._spectrum_window * self._fs)
        if nperseg < 64:
            nperseg = 64
        if nperseg > data.shape[1]:
            nperseg = data.shape[1]
        # 计算重叠样本数：将窗口长度乘以重叠百分比（转换为小数），转换为整数
        noverlap = int(nperseg * self._overlap_ratio / 100.0)

        # 从窗口类型映射字典中获取对应的scipy窗口名称，如果找不到则默认使用"hann"（汉宁窗）
        win_name = _WINDOW_MAP.get(self._window_type, "hann")

        psd_list: list[np.ndarray] = []
        freqs: np.ndarray | None = None
        # 每次取出的是 一个通道的全部时间序列数据 （一行）
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
