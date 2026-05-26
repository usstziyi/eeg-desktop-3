import pyqtgraph as pg
import numpy as np

from PySide6 import QtGui



CUSTOM_COLOR = [
    (100, 180, 255),
    (255, 150, 100),
    (100, 255, 150),
    (255, 200, 80),
    (180, 120, 255),
    (255, 120, 180),
    (120, 255, 220),
    (220, 220, 100),
]

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

CET_R3_DEFAULT = CET_R3 * 4


class EEGWidget(pg.GraphicsLayoutWidget):
    def __init__(self, eeg_names = None, parent=None):
        super().__init__(parent)
        self.setBackground("k")
        self._plots = {}
        self._curves = {}

        font = QtGui.QFont()
        font.setPointSize(10)

        if not eeg_names:
            eeg_names = [f"CH{i+1}" for i in range(8)]

        self._n_channels = len(eeg_names)

        for i, name in enumerate(eeg_names):
            color = CET_R3[i % len(CET_R3)]
            plot = self.addPlot(row=i, col=0)
            plot.setLabel("left", f"{name}", units="µV")
            plot.getAxis("left").setWidth(60)
            plot.getAxis("left").autoSIPrefix = False
            plot.getAxis("left").setStyle(tickFont=font) 

            plot.setDownsampling(auto=True, mode="peak")
            plot.setClipToView(True)
            plot.addLine(y=0, pen=pg.mkPen((255, 255, 255, 60), width=1, style=pg.QtCore.Qt.PenStyle.DashLine))
            plot.getAxis("bottom").autoSIPrefix = False

            curve = plot.plot(pen=pg.mkPen(color, width=1))
            self._curves[i] = curve

            if i == 0:
                self._first_plot = plot
            else:
                plot.setXLink(self._first_plot)

            if i < self._n_channels - 1:
                plot.hideAxis("bottom")
            else:
                plot.setLabel("bottom", "Time", units="s")

            self._plots[i] = plot

        self.set_x_range(5)
        self.set_y_range(100)




    def set_x_range(self, value):
        for plot in self._plots.values():
            plot.setXRange(-value, 0, padding=0)

    def set_y_range(self, value):
        for plot in self._plots.values():
            plot.setYRange(-value, value, padding=0)
            ticks = [[(-value, str(-value)), (value, str(value))]]
            plot.getAxis("left").setTicks(ticks)
        

    def updata_data(self, times, eeg_data):
        if eeg_data.size == 0 or eeg_data.shape[1] == 0:
            return
        for i in range(min(self._n_channels, eeg_data.shape[0])):
            self._curves[i].setData(times, eeg_data[i, :])





