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

    def __init__(self, settings=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        main_layout = QVBoxLayout(self)

        device_group = self._build_device_group()
        stream_group = self._build_stream_group()
        process_group = self._build_process_group()
        spectrum_group = self._build_spectrum_group()
        display_group = self._build_display_group()
        recorder_group = self._build_recorder_group()
        main_layout.addWidget(device_group)
        main_layout.addWidget(stream_group)
        main_layout.addWidget(process_group)
        main_layout.addWidget(spectrum_group)
        main_layout.addWidget(display_group)
        main_layout.addStretch(1)
        main_layout.addWidget(recorder_group)

        self._connect_signals()

        if settings is not None:
            self.load_settings(settings)
        
    
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
        self._stop_stream_btn.setStyleSheet(self._able_btn_style("#e53935"))
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
        process_layout.addRow("高通滤波:", self._bp_high_spin)
        # notch
        self._notch_combo = QComboBox()
        self._notch_combo.addItems(["50 Hz", "60 Hz", "None"])
        process_layout.addRow("工频滤波:", self._notch_combo)

        return process_group

    def _build_spectrum_group(self):
        spectrum_group = QGroupBox("频域分析")
        spectrum_layout = QFormLayout(spectrum_group)
        self._window_type = QComboBox()
        self._window_type.addItems(["Hann", "Hamming", "Blackman", "Bartlett", "Rectangular"])
        self._window_type.setCurrentText("Hann")
        spectrum_layout.addRow("窗口类型:",self._window_type)
        self._spectrum_window = QDoubleSpinBox()
        self._spectrum_window.setSuffix(" s")
        self._spectrum_window.setRange(0.5, 5.0)
        self._spectrum_window.setSingleStep(0.5)
        spectrum_layout.addRow("频谱窗长:",self._spectrum_window)
        self._overlap_ratio = QSpinBox()
        self._overlap_ratio.setSuffix(" %")
        self._overlap_ratio.setRange(10,50)
        self._overlap_ratio.setSingleStep(5)
        spectrum_layout.addRow("重叠比例:",self._overlap_ratio)
        self._freqs_range = QDoubleSpinBox()
        self._freqs_range.setSuffix(" Hz")
        self._freqs_range.setRange(10, 125.0)
        self._freqs_range.setValue(60)
        self._freqs_range.setSingleStep(5)
        spectrum_layout.addRow("频率范围:",self._freqs_range)
        return spectrum_group



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
        self._amplitude_spin.setRange(10, 2000)
        self._amplitude_spin.setValue(100)
        self._amplitude_spin.setSingleStep(20)
        self._amplitude_spin.setSuffix(" µV")
        display_layout.addRow("信号强度",self._amplitude_spin)

        self._refresh_spin = QSpinBox()
        self._refresh_spin.setRange(20, 200)
        self._refresh_spin.setValue(50)
        self._refresh_spin.setSuffix(" ms")
        display_layout.addRow("刷新间隔:", self._refresh_spin)
        return display_group

    def _build_recorder_group(self):
        recorder_group = QGroupBox("信号录制")
        recorder_layout = QFormLayout(recorder_group)
        self._record_check = QCheckBox("Record")
        self._record_original_signal = QCheckBox("原始信号")
        self._record_processed_signal = QCheckBox("实时信号")
        self._recorder_button = QPushButton("▶ 开始录制")
        self._recorder_button.setCheckable(True)
        self._recorder_button.setStyleSheet(self._toggle_btn_style("#e53935", "#4a90d9"))
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
        self._record_check.toggled.connect(self._on_record_check_toggled)
        self._recorder_button.clicked.connect(self._record_check.toggle)

        emit = self._emit_single
        self._device_combo.currentTextChanged.connect(
            lambda v: emit("device.name", v)
        )
        self._port_combo.currentTextChanged.connect(
            lambda v: emit("device.serial_port", v)
        )

        self._detrend_check.toggled.connect(
            lambda v: emit("process.detrend", v)
        )
        self._bp_low_spin.valueChanged.connect(
            lambda v: emit("process.bp_low_hz", v)
        )
        self._bp_high_spin.valueChanged.connect(
            lambda v: emit("process.bp_high_hz", v)
        )
        self._notch_combo.currentTextChanged.connect(
            lambda v: emit("process.notch_hz", self._notch_text_to_hz(v))
        )

        self._window_type.currentTextChanged.connect(
            lambda v: emit("spectrum.window_type", v)
        )
        self._spectrum_window.valueChanged.connect(
            lambda v: emit("spectrum.spectrum_window", v)
        )
        self._overlap_ratio.valueChanged.connect(
            lambda v: emit("spectrum.overlap_ratio", v)
        )

        self._window_time_spin.valueChanged.connect(
            lambda v: emit("display.window_seconds", v)
        )
        self._amplitude_spin.valueChanged.connect(
            lambda v: emit("display.amplitude_range", v)
        )
        self._refresh_spin.valueChanged.connect(
            lambda v: emit("display.refresh_ms", v)
        )

        self._record_original_signal.toggled.connect(
            lambda v: emit("recording.record_original", v)
        )
        self._record_processed_signal.toggled.connect(
            lambda v: emit("recording.record_processed", v)
        )

    def load_settings(self, settings) -> None:
        self._device_combo.setCurrentText(
            settings.get("device", "name", default="synthetic")
        )
        # 使用构造函数初始化结果
        # self._port_combo.setCurrentText(
        #     settings.get("device", "serial_port", default="")
        # )

        self._detrend_check.setChecked(
            settings.get("process", "detrend", default=True)
        )
        self._bp_low_spin.setValue(
            settings.get("process", "bp_low_hz", default=0.1)
        )
        self._bp_high_spin.setValue(
            settings.get("process", "bp_high_hz", default=45.0)
        )
        notch_hz = settings.get("process", "notch_hz", default=50.0)
        if notch_hz == 0.0:
            self._notch_combo.setCurrentText("None")
        elif notch_hz == 60.0:
            self._notch_combo.setCurrentText("60 Hz")
        else:
            self._notch_combo.setCurrentText("50 Hz")

        self._window_type.setCurrentText(
            settings.get("spectrum", "window_type", default="Hann")
        )
        self._spectrum_window.setValue(
            settings.get("spectrum", "spectrum_window", default=0.5)
        )
        self._overlap_ratio.setValue(
            settings.get("spectrum", "overlap_ratio", default=10)
        )

        self._window_time_spin.setValue(
            settings.get("display", "window_seconds", default=4.0)
        )
        self._amplitude_spin.setValue(
            settings.get("display", "amplitude_range", default=100)
        )
        self._refresh_spin.setValue(
            settings.get("display", "refresh_ms", default=50)
        )

        self._record_original_signal.setChecked(
            settings.get("recording", "record_original", default=False)
        )
        self._record_processed_signal.setChecked(
            settings.get("recording", "record_processed", default=False)
        )

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

    @Slot(bool)
    def set_record_checkboxes_enabled(self, enabled: bool) -> None:
        self._record_original_signal.setEnabled(enabled)
        self._record_processed_signal.setEnabled(enabled)

    @Slot(bool)
    def _on_record_check_toggled(self, checked: bool) -> None:
        self._recorder_button.setText("⏸ 停止录制" if checked else "▶ 开始录制")

    @staticmethod
    def _notch_text_to_hz(text: str) -> float:
        if text == "None":
            return 0.0
        return float(text.split()[0])

    def _emit_single(self, key: str, value) -> None:
        self.config_changed.emit({key: value})


    def _able_btn_style(self, color):
        return f"""
            QPushButton:!disabled {{
                background: {color};
                color: #fff;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }}
        """
    def _toggle_btn_style(self, on_color, off_color):
        return f"""
            QPushButton {{
                color: #fff;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }}
            QPushButton:checked {{
                background: {on_color};
            }}
            QPushButton:!checked {{
                background: {off_color};
            }}
        """