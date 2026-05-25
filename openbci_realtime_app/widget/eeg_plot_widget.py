import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class EegPlotWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setLabel("left", "Amplitude", units="µV")
        self._plot_widget.setLabel("bottom", "Time", units="s")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setYRange(-200, 200)

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
        self._y_offset = 0.0
        self._y_scale = 1.0

    def setup_channels(self, num_channels: int) -> None:
        for curve in self._curves:
            self._plot_widget.removeItem(curve)
        self._curves.clear()
        for i in range(num_channels):
            color = self._colors[i % len(self._colors)]
            pen = pg.mkPen(color=color, width=1)
            curve = self._plot_widget.plot([], [], pen=pen)
            self._curves.append(curve)

    def set_y_range(self, y_min: float, y_max: float) -> None:
        self._plot_widget.setYRange(y_min, y_max)

    def set_window_seconds(self, seconds: float) -> None:
        self._plot_widget.setXRange(0, seconds)

    def update_data(self, eeg_data: np.ndarray, timestamps: np.ndarray) -> None:
        if eeg_data.size == 0 or eeg_data.shape[1] == 0:
            return
        num_channels = min(eeg_data.shape[0], len(self._curves))
        for i in range(num_channels):
            channel_data = eeg_data[i, :].astype(np.float64)
            if self._y_scale != 1.0:
                channel_data = channel_data * self._y_scale
            offset = i * self._y_offset
            self._curves[i].setData(timestamps, channel_data + offset)
