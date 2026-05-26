import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


CET_R3 = [
    (214, 68, 60),
    (239, 143, 44),
    (200, 202, 52),
    (65, 183, 130),
    (50, 138, 190),
    (80, 82, 185),
    (139, 61, 159),
    (197, 50, 120),
]


class PSDWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setLabel("left", "Power Spectral Density", units="µV²/Hz")
        self._plot_widget.setLabel("bottom", "Frequency", units="Hz")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLogMode(x=False, y=True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot_widget)

        self._curve: pg.PlotDataItem | None = None
        self._fill: pg.FillBetweenItem | None = None
        self._floor_curve: pg.PlotDataItem | None = None
        self._channel_index: int = 0
        self._num_channels: int = 0

    def setup_channels(self, num_channels: int) -> None:
        self._num_channels = num_channels
        self._channel_index = min(self._channel_index, num_channels - 1)

    def set_channel(self, channel_index: int) -> None:
        if 0 <= channel_index < self._num_channels:
            self._channel_index = channel_index

    def channel(self) -> int:
        return self._channel_index

    def update_psd(self, freqs: np.ndarray, psd_values: np.ndarray) -> None:
        if freqs.size == 0 or psd_values.size == 0:
            return

        if psd_values.ndim == 2:
            if self._channel_index >= psd_values.shape[0]:
                return
            psd = psd_values[self._channel_index, :]
        else:
            psd = psd_values

        psd = np.maximum(psd, 1e-12)
        color = CET_R3[self._channel_index % len(CET_R3)]
        pen = pg.mkPen(color=color, width=1.5)

        if self._curve is None:
            self._floor = np.full_like(freqs, 1e-12)
            self._curve = self._plot_widget.plot(freqs, psd, pen=pen)
            self._floor_curve = self._plot_widget.plot(freqs, self._floor, pen=None)
            fill_color = (*color, 50)
            self._fill = pg.FillBetweenItem(
                self._curve, self._floor_curve, brush=fill_color
            )
            self._plot_widget.addItem(self._fill)
        else:
            self._curve.setData(freqs, psd)
            self._curve.setPen(pen)
            self._floor_curve.setData(freqs, self._floor)
            fill_color = (*color, 50)
            self._fill.setBrush(fill_color)
