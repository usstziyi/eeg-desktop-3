import numpy as np

from processing import apply_filter_chain, compute_band_powers, compute_psd_welch, FilterConfig


def _make_sine(freq: float, sr: float, duration: float, noise: float = 0.0) -> np.ndarray:
    t = np.arange(0, duration, 1.0 / sr)
    sig = np.sin(2 * np.pi * freq * t)
    if noise > 0:
        sig += np.random.randn(len(t)) * noise
    return sig.reshape(1, -1)


class TestFilters:
    def test_empty_data(self):
        config = FilterConfig(sampling_rate=250)
        result = apply_filter_chain(np.array([]), 250, config)
        assert result.size == 0

    def test_detrend_removes_dc(self):
        sr = 250
        duration = 4
        config = FilterConfig(bandpass_low=1.0, bandpass_high=45.0, notch=0.0, sampling_rate=sr)
        raw = _make_sine(10.0, sr, duration) + 100.0
        result = apply_filter_chain(raw, sr, config)
        assert abs(np.mean(result)) < 50.0

    def test_notch_50hz(self):
        sr = 250
        duration = 4
        config = FilterConfig(bandpass_low=1.0, bandpass_high=45.0, notch=50.0, sampling_rate=sr)
        raw = _make_sine(50.0, sr, duration)
        result = apply_filter_chain(raw, sr, config)
        assert np.std(result) < 0.5

    def test_multi_channel(self):
        sr = 250
        duration = 4
        config = FilterConfig(sampling_rate=sr)
        raw = np.vstack([_make_sine(10.0, sr, duration), _make_sine(20.0, sr, duration)])
        result = apply_filter_chain(raw, sr, config)
        assert result.shape == raw.shape


class TestSpectrum:
    def test_psd_shape(self):
        sr = 250
        duration = 4
        data = _make_sine(10.0, sr, duration)
        freqs, psd = compute_psd_welch(data, sr, window_seconds=4, overlap_ratio=0.5)
        assert freqs.size > 0
        assert psd.shape[0] == 1
        assert psd.shape[1] == freqs.size

    def test_empty_psd(self):
        freqs, psd = compute_psd_welch(np.array([]), 250, 4)
        assert freqs.size == 0
        assert psd.size == 0


class TestBandPower:
    def test_band_power_keys(self):
        sr = 250
        duration = 4
        data = _make_sine(10.0, sr, duration)
        results = compute_band_powers(data, sr)
        assert len(results) == 1
        for key in ("delta", "theta", "alpha", "beta", "gamma"):
            assert key in results[0]
            assert isinstance(results[0][key], float)

    def test_alpha_dominant(self):
        sr = 250
        duration = 4
        data = _make_sine(10.0, sr, duration)
        results = compute_band_powers(data, sr)
        assert results[0]["alpha"] > results[0]["delta"]
        assert results[0]["alpha"] > results[0]["gamma"]
