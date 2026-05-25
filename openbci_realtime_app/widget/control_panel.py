from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from acquisition.serial_ports import list_serial_ports


class PortComboBox(QComboBox):
    def showPopup(self):
        self.clear()
        self.addItems(list_serial_ports())
        super().showPopup()


class ControlPanel(QWidget):
    connect_requested = Signal()
    disconnect_requested = Signal()
    start_requested = Signal()
    stop_requested = Signal()
    record_toggled = Signal(bool)
    config_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        main_layout = QVBoxLayout(self)

        device_group = self._build_device_group()
        stream_group = self._build_stream_group()
        process_group = self._build_process_group()
        spectral_group = self._build_spectral_group()
        display_group = self._build_display_group()
        recorder_group = self._build_recorder_group()
        main_layout.addWidget(device_group)
        main_layout.addWidget(stream_group)
        main_layout.addWidget(process_group)
        main_layout.addWidget(spectral_group)
        main_layout.addWidget(display_group)
        main_layout.addStretch(1)
        main_layout.addWidget(recorder_group)

        self._connect_signals()
        
    
    def _build_device_group(self):
        device_group = QGroupBox("设备选择")
        device_layout = QFormLayout(device_group)
        self._device_combo = QComboBox()
        self._device_combo.addItems(["synthetic", "cyton"])
        self._port_combo = PortComboBox()
        self._connect_btn = QPushButton("Connect")
        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setEnabled(False)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self._connect_btn)
        btn_row.addWidget(self._disconnect_btn)
        device_layout.addRow("名称:", self._device_combo)
        device_layout.addRow("串口:", self._port_combo)
        device_layout.addRow(btn_row)
        return device_group
        
    def _build_stream_group(self):
        stream_group = QGroupBox("数据流")
        stream_layout = QFormLayout(stream_group)
        self._start_stream_btn = QPushButton("Start")
        self._stop_stream_btn = QPushButton("Stop")
        self._start_stream_btn.setEnabled(False)
        self._stop_stream_btn.setEnabled(False)
        stream_btn_row = QHBoxLayout()
        stream_btn_row.addWidget(self._start_stream_btn)
        stream_btn_row.addWidget(self._stop_stream_btn)
        stream_layout.addRow(stream_btn_row)
        return stream_group
        

    def _build_process_group(self):
        process_group = QGroupBox("预处理")
        process_layout = QFormLayout(process_group)
        # detrend
        self._detrend_check = QCheckBox()
        self._detrend_check.setChecked(True)
        process_layout.addRow("去除漂移:",self._detrend_check)
        # BandPass low
        self._bp_low_spin = QDoubleSpinBox()
        self._bp_low_spin.setRange(0.1, 20.0)
        self._bp_low_spin.setValue(0.1)
        self._bp_low_spin.setSingleStep(0.1)
        self._bp_low_spin.setSuffix(" Hz")
        process_layout.addRow("低通滤波:", self._bp_low_spin)
        # BandPass high
        self._bp_high_spin = QDoubleSpinBox()
        self._bp_high_spin.setRange(20.0, 100.0)
        self._bp_high_spin.setValue(45.0)
        self._bp_high_spin.setSingleStep(0.1)
        self._bp_high_spin.setSuffix(" Hz")
        self._bp_high_spin.setDecimals(1)
        process_layout.addRow("高通滤波:", self._bp_high_spin)
        # notch
        self._notch_combo = QComboBox()
        self._notch_combo.addItems(["50 Hz", "60 Hz", "None"])
        process_layout.addRow("工频滤波:", self._notch_combo)

        return process_group

    def _build_spectral_group(self):
        spectral_group = QGroupBox("频域分析")
        spectral_layout = QFormLayout(spectral_group)
        self._window_type = QComboBox()
        self._window_type.addItems(["Hann", "Hamming", "Blackman", "Bartlett", "Rectangular"])
        self._window_type.setCurrentText("Hamming")
        spectral_layout.addRow("窗口类型:",self._window_type)
        self._spectral_time = QDoubleSpinBox()
        self._spectral_time.setSuffix(" s")
        self._spectral_time.setRange(0.5, 5.0)
        self._spectral_time.setSingleStep(0.5)
        spectral_layout.addRow("频谱窗长:",self._spectral_time)
        self._overlap_ratio = QSpinBox()
        self._overlap_ratio.setSuffix(" %")
        self._overlap_ratio.setRange(10,50)
        self._overlap_ratio.setSingleStep(5)
        spectral_layout.addRow("重叠比例:",self._overlap_ratio)
        return spectral_group



    def _build_display_group(self):
        display_group = QGroupBox("显示设置")
        display_layout = QFormLayout(display_group)
        self._window_time_spin = QDoubleSpinBox()
        self._window_time_spin.setRange(2.0, 30.0)
        self._window_time_spin.setValue(4.0)
        self._window_time_spin.setSingleStep(1)
        self._window_time_spin.setSuffix(" s")
        display_layout.addRow("显示时长:", self._window_time_spin)

        self._amplitude_spin = QSpinBox()
        self._amplitude_spin.setRange(10, 1000)
        self._amplitude_spin.setValue(100)
        self._amplitude_spin.setSingleStep(10)
        self._amplitude_spin.setSuffix(" µV")
        display_layout.addRow("信号强度",self._amplitude_spin)

        self._refresh_spin = QSpinBox()
        self._refresh_spin.setRange(20, 200)
        self._refresh_spin.setValue(50)
        self._refresh_spin.setSuffix(" ms")
        display_layout.addRow("Refresh:", self._refresh_spin)
        return display_group

    def _build_recorder_group(self):
        recorder_group = QGroupBox("信号录制")
        recorder_layout = QFormLayout(recorder_group)
        self._record_check = QCheckBox("Record")
        self._record_original_signal = QCheckBox("原始信号")
        self._record_processed_signal = QCheckBox("实时信号")
        self._recorder_button = QPushButton("录制")
        recorder_layout.addRow(self._record_original_signal)
        recorder_layout.addRow(self._record_processed_signal)
        recorder_layout.addRow(self._recorder_button)
        return recorder_group




    def _connect_signals(self):
        self._connect_btn.clicked.connect(self.connect_requested)
        self._disconnect_btn.clicked.connect(self.disconnect_requested)
        self._start_stream_btn.clicked.connect(self.start_requested)
        self._stop_stream_btn.clicked.connect(self.stop_requested)
        self._record_check.toggled.connect(self.record_toggled)


        self._detrend_check.toggled.connect(self._emit_config)
        self._bp_low_spin.valueChanged.connect(self._emit_config)
        self._bp_high_spin.valueChanged.connect(self._emit_config)
        self._notch_combo.currentTextChanged.connect(self._emit_config)

        self._window_type.currentTextChanged.connect(self._emit_config)
        self._spectral_time.valueChanged.connect(self._emit_config)
        self._overlap_ratio.valueChanged.connect(self._emit_config)

        self._window_time_spin.valueChanged.connect(self._emit_config)
        self._refresh_spin.valueChanged.connect(self._emit_config)
        self._amplitude_spin.valueChanged.connect(self._emit_config)

        self._record_original_signal.toggled.connect(self._emit_config)
        self._record_processed_signal.toggled.connect(self._emit_config)

    @Slot(bool)
    def set_connected(self, connected: bool) -> None:
        self._connect_btn.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._start_stream_btn.setEnabled(connected)
        if not connected:
            self._stop_stream_btn.setEnabled(False)

    @Slot(bool)
    def set_streaming(self, streaming: bool) -> None:
        self._start_stream_btn.setEnabled(not streaming)
        self._stop_stream_btn.setEnabled(streaming)

    def _emit_config(self) -> None:
        notch_text = self._notch_combo.currentText()
        if notch_text == "None":
            notch_hz = 0.0
        else:
            notch_hz = float(notch_text.split()[0])
        self.config_changed.emit({
            # device
            "device.name": self._device_combo.currentText(),
            "device.serial_port": self._port_combo.currentText(),

            # process
            "process.detrend": self._detrend_check.isChecked(),
            "process.bp_low_hz": self._bp_low_spin.value(),
            "process.bp_high_hz": self._bp_high_spin.value(),
            "process.notch_hz": notch_hz,

            # spectral
            "spectral.window_type": self._window_type.currentText(),
            "spectral.spectral_time": self._spectral_time.value(),
            "spectral.overlap_ratio": self._overlap_ratio.value(),
            
            # display
            "display.window_seconds": self._window_time_spin.value(),
            "display.y_scale_uv": self._amplitude_spin.value(),
            "display.refresh_ms": self._refresh_spin.value(),

            # recorder
            "recording.record_original": self._record_original_signal.isChecked(),
            "recording.record_processed": self._record_processed_signal.isChecked(),
        })
