from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ControlPanel(QWidget):
    connect_requested = Signal()
    disconnect_requested = Signal()
    start_requested = Signal()
    stop_requested = Signal()
    record_toggled = Signal(bool)
    config_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMaximumWidth(320)

        main_layout = QVBoxLayout(self)

        board_group = QGroupBox("Board")
        board_layout = QFormLayout(board_group)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["synthetic", "cyton"])
        board_layout.addRow("Mode:", self._mode_combo)
        self._port_edit = QLineEdit("COM3")
        board_layout.addRow("Port:", self._port_edit)
        self._connect_btn = QPushButton("Connect")
        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setEnabled(False)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self._connect_btn)
        btn_row.addWidget(self._disconnect_btn)
        board_layout.addRow(btn_row)
        main_layout.addWidget(board_group)

        stream_group = QGroupBox("Stream")
        stream_layout = QFormLayout(stream_group)
        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        self._start_btn.setEnabled(False)
        stream_btn_row = QHBoxLayout()
        stream_btn_row.addWidget(self._start_btn)
        stream_btn_row.addWidget(self._stop_btn)
        stream_layout.addRow(stream_btn_row)

        self._record_check = QCheckBox("Record")
        stream_layout.addRow(self._record_check)
        main_layout.addWidget(stream_group)

        display_group = QGroupBox("Display")
        display_layout = QFormLayout(display_group)
        self._window_spin = QDoubleSpinBox()
        self._window_spin.setRange(2.0, 30.0)
        self._window_spin.setValue(4.0)
        self._window_spin.setSuffix(" s")
        display_layout.addRow("Window:", self._window_spin)

        self._refresh_spin = QSpinBox()
        self._refresh_spin.setRange(20, 200)
        self._refresh_spin.setValue(50)
        self._refresh_spin.setSuffix(" ms")
        display_layout.addRow("Refresh:", self._refresh_spin)

        self._yscale_spin = QSpinBox()
        self._yscale_spin.setRange(10, 1000)
        self._yscale_spin.setValue(100)
        self._yscale_spin.setSuffix(" µV")
        display_layout.addRow("Y Scale:", self._yscale_spin)
        main_layout.addWidget(display_group)

        proc_group = QGroupBox("Processing")
        proc_layout = QFormLayout(proc_group)
        self._bp_low_spin = QDoubleSpinBox()
        self._bp_low_spin.setRange(0.1, 20.0)
        self._bp_low_spin.setValue(1.0)
        self._bp_low_spin.setSuffix(" Hz")
        self._bp_low_spin.setDecimals(1)
        proc_layout.addRow("BP Low:", self._bp_low_spin)

        self._bp_high_spin = QDoubleSpinBox()
        self._bp_high_spin.setRange(20.0, 100.0)
        self._bp_high_spin.setValue(45.0)
        self._bp_high_spin.setSuffix(" Hz")
        self._bp_high_spin.setDecimals(1)
        proc_layout.addRow("BP High:", self._bp_high_spin)

        self._notch_combo = QComboBox()
        self._notch_combo.addItems(["50 Hz", "60 Hz", "None"])
        proc_layout.addRow("Notch:", self._notch_combo)

        self._psd_win_spin = QDoubleSpinBox()
        self._psd_win_spin.setRange(1.0, 10.0)
        self._psd_win_spin.setValue(4.0)
        self._psd_win_spin.setSuffix(" s")
        proc_layout.addRow("PSD Win:", self._psd_win_spin)
        main_layout.addWidget(proc_group)

        main_layout.addStretch()

        self._connect_btn.clicked.connect(self.connect_requested.emit)
        self._disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        self._start_btn.clicked.connect(self.start_requested.emit)
        self._stop_btn.clicked.connect(self.stop_requested.emit)
        self._record_check.toggled.connect(self.record_toggled.emit)

        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self._port_edit.textChanged.connect(self._emit_config)
        self._window_spin.valueChanged.connect(self._emit_config)
        self._refresh_spin.valueChanged.connect(self._emit_config)
        self._yscale_spin.valueChanged.connect(self._emit_config)
        self._bp_low_spin.valueChanged.connect(self._emit_config)
        self._bp_high_spin.valueChanged.connect(self._emit_config)
        self._notch_combo.currentTextChanged.connect(self._emit_config)
        self._psd_win_spin.valueChanged.connect(self._emit_config)

    def set_connected(self, connected: bool) -> None:
        self._connect_btn.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._start_btn.setEnabled(connected)
        self._mode_combo.setEnabled(not connected)
        self._port_edit.setEnabled(not connected)

    def set_streaming(self, streaming: bool) -> None:
        self._start_btn.setEnabled(not streaming)
        self._stop_btn.setEnabled(streaming)

    def _on_mode_changed(self, text: str) -> None:
        self._port_edit.setEnabled(text == "cyton")
        self._emit_config()

    def _emit_config(self) -> None:
        notch_text = self._notch_combo.currentText()
        if notch_text == "None":
            notch_hz = 0.0
        else:
            notch_hz = float(notch_text.split()[0])
        self.config_changed.emit({
            "board.mode": self._mode_combo.currentText(),
            "board.serial_port": self._port_edit.text(),
            "display.window_seconds": self._window_spin.value(),
            "display.refresh_ms": self._refresh_spin.value(),
            "display.y_scale_uv": self._yscale_spin.value(),
            "processing.bandpass_low_hz": self._bp_low_spin.value(),
            "processing.bandpass_high_hz": self._bp_high_spin.value(),
            "processing.notch_hz": notch_hz,
            "processing.psd_window_seconds": self._psd_win_spin.value(),
        })
