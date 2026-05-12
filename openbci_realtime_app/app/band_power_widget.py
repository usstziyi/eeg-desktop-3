import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class BandPowerWidget(QWidget):
    BAND_NAMES = ["delta", "theta", "alpha", "beta", "gamma"]
    CHANNEL_COLORS = [
        (100, 180, 255),
        (255, 150, 100),
        (100, 255, 150),
        (255, 200, 80),
        (180, 120, 255),
        (255, 120, 180),
        (120, 255, 220),
        (220, 220, 100),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setLabel("left", "Relative Power")
        self._plot_widget.setLabel("bottom", "Frequency Band")
        self._plot_widget.showGrid(y=True, alpha=0.3)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot_widget)

        self._bar_items: list[pg.BarGraphItem] = []
        self._num_channels = 0

    def setup_channels(self, num_channels: int) -> None:
        self._plot_widget.clear()
        self._bar_items.clear()
        self._num_channels = num_channels
        x_axis = self._plot_widget.getAxis("bottom")
        x_axis.setTicks([[(i, name) for i, name in enumerate(self.BAND_NAMES)]])
        bar_width = 0.8 / max(num_channels, 1)
        for i in range(num_channels):
            color = self.CHANNEL_COLORS[i % len(self.CHANNEL_COLORS)]
            bar = pg.BarGraphItem(
                x=[], height=[], width=bar_width, brush=color
            )
            self._plot_widget.addItem(bar)
            self._bar_items.append(bar)

    def update_band_powers(self, band_powers: list[dict]) -> None:
        if not band_powers or not self._bar_items:
            return
        num_ch = len(self._bar_items)
        bar_width = 0.8 / max(num_ch, 1)
        for ch_idx, bp in enumerate(band_powers[:num_ch]):
            heights = [bp.get(name, 0.0) for name in self.BAND_NAMES]
            offset = (ch_idx - (num_ch - 1) / 2.0) * bar_width
            x = [i + offset for i in range(len(self.BAND_NAMES))]
            self._bar_items[ch_idx].setOpts(x=x, height=heights, width=bar_width)
