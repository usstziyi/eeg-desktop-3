import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class SpectrumWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setLabel("left", "Power", units="µV²/Hz")
        self._plot_widget.setLabel("bottom", "Frequency", units="Hz")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLogMode(x=False, y=True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot_widget)

        self._curves: list[pg.PlotDataItem] = []
        self._colors = [
            (100, 180, 255),
            (255, 150, 100),
            (100, 255, 150),
            (255, 200, 80),
            (180, 120, 255),
            (255, 120, 180),
            (120, 255, 220),
            (220, 220, 100),
        ]

    def setup_channels(self, num_channels: int) -> None:
        for curve in self._curves:
            self._plot_widget.removeItem(curve)
        self._curves.clear()
        for i in range(num_channels):
            color = self._colors[i % len(self._colors)]
            pen = pg.mkPen(color=color, width=1)
            curve = self._plot_widget.plot([], [], pen=pen, name=f"Ch{i + 1}")
            self._curves.append(curve)

    def update_spectrum(self, freqs: np.ndarray, psd_values: np.ndarray) -> None:
        if freqs.size == 0 or psd_values.size == 0:
            return
        num_channels = min(psd_values.shape[0], len(self._curves))
        for i in range(num_channels):
            psd = psd_values[i, :]
            psd = np.maximum(psd, 1e-12)
            self._curves[i].setData(freqs, psd)
