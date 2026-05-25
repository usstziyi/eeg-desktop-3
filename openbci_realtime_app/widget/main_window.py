import os
import traceback

import numpy as np
from PySide6.QtCore import QSettings, QTimer, QThread, Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from acquisition import BoardSession, create_board
from parameter import Settings
from processing import FilterConfig, ProcessingWorker
from recording import Recorder

from .control_panel import ControlPanel
from .eeg_widget import EEGWidget
from .fft_widget import FFTWidget
from .spectrum_widget import SpectrumWidget
from .band_power_widget import BandPowerWidget


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.setWindowTitle("OpenBCI EEG - Real-time Monitor")
        self.resize(1400, 900)

        self._settings = settings
        self._session: BoardSession | None = None
        self._recorder = Recorder(
            directory=settings.get("recording", "directory", default="recordings")
        )

        self._sample_rate: int = 250
        self._eeg_channel_num: int = 8
        self._eeg_names: list[str]=None
        self._eeg_channels: list[int]=None

        self._raw_data: np.ndarray = np.array([]) # 所有通道数据
        self._eeg_data: np.ndarray = np.array([]) # eeg通道数据


        self._refresh_ms: int = 50
        self._window_time: int=5

        self._app_settings = QSettings()

        self._init_ui()
        self._setup_menubar()
        self._restore_window_state()
        self._init_timer()
        self._init_processing_thread()

        self._connect_signals()

    def _init_ui(self) -> None:
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        self.left_dock = QDockWidget("控制面板")
        self.left_dock.setObjectName("left_dock")
        self.left_dock.setTitleBarWidget(QWidget())
        left_widget = self._setup_left_panel()
        self.left_dock.setWidget(left_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.left_dock)

        center_widget = self._setup_center_panel()
        self.setCentralWidget(center_widget)

        self.right_dock = QDockWidget("右侧面板")
        self.right_dock.setObjectName("right_dock")
        self.right_dock.setTitleBarWidget(QWidget())
        right_widget = self._setup_right_panel()
        self.right_dock.setWidget(right_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)

        self.bottom_dock = QDockWidget("底部面板")
        self.bottom_dock.setObjectName("bottom_dock")
        self.bottom_dock.setTitleBarWidget(QWidget())
        bottom_widget = self._setup_bottom_panel()
        self.bottom_dock.setWidget(bottom_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.bottom_dock)



    
    def _setup_left_panel(self):
        self._control_panel = ControlPanel(settings=self._settings)
        return self._control_panel


    def _setup_center_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.tab_widget = QTabWidget()
        self._eeg_names=['Fp1', 'Fp2', 'C3', 'C4', 'P7', 'P8', 'O1', 'O2']
        self.eeg_widget = EEGWidget(self._eeg_names)
        self.fft_widget = FFTWidget()
        
        self.tab_widget.addTab(self.eeg_widget, "EEG 时序图")
        self.tab_widget.addTab(self.fft_widget, "FFT 频谱图")

        layout.addWidget(self.tab_widget)
        return widget

    def _setup_right_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        label = QLabel("右侧面板 — 待设计")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return widget

    def _setup_bottom_panel(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        bottom_tab_widget = QTabWidget()
        self.spectrogram_widget = QWidget()
        self.band_power_widget = QWidget()
        bottom_tab_widget.addTab(self.spectrogram_widget, "时频图")
        bottom_tab_widget.addTab(self.band_power_widget, "频带能量图")


        layout.addWidget(bottom_tab_widget)
        return widget

    def _setup_menubar(self):
        menubar = self.menuBar()

        view_menu = menubar.addMenu("视图(&V)")

        view_menu.addAction(self.left_dock.toggleViewAction())
        view_menu.addAction(self.right_dock.toggleViewAction())
        view_menu.addAction(self.bottom_dock.toggleViewAction())

    def _restore_window_state(self) -> None:
        geometry = self._app_settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = self._app_settings.value("window/state")
        if state is not None:
            self.restoreState(state)

    def _init_channels(self) -> None:
        num_channels = 8
        self._spectrum_widget.setup_channels(num_channels)
        self._band_power_widget.setup_channels(num_channels)

    def _init_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._refresh_ms = self._settings.get("display", "refresh_ms", default=50)
        self._timer.setInterval(self._refresh_ms)
        self._timer.timeout.connect(self._on_timer_tick)

    def _init_processing_thread(self) -> None:
        self._processing_worker = ProcessingWorker()
        self._processing_thread = QThread(self)
        self._processing_worker.moveToThread(self._processing_thread)
        self._processing_thread.start()
        self._processing_worker.processed_ready.connect(
            self._on_processed_data, Qt.ConnectionType.QueuedConnection
        )

    def _connect_signals(self) -> None:
        panel = self._control_panel
        panel.connect_requested.connect(self._on_connect)
        panel.disconnect_requested.connect(self._on_disconnect)
        panel.start_requested.connect(self._on_start)
        panel.stop_requested.connect(self._on_stop)
        panel.record_toggled.connect(self._on_record_toggled)
        panel.config_changed.connect(self._on_config_changed)

    def _on_connect(self) -> None:
        try:
            name = self._settings.get("device", "name", default="synthetic")
            port = self._settings.get("device", "serial_port", default="")
            timeout = self._settings.get("device", "timeout", default=5)

            board = create_board(name, serial_port=port, timeout=timeout)
            session = BoardSession(board)
            session.prepare()

            self._session = session
            self._control_panel.set_connected(True)

            self._sample_rate = session.sampling_rate
            self._eeg_channel_num = session.eeg_channel_num
            self._eeg_names = session.eeg_names
            self._eeg_channels = session.eeg_channels
            self._window_time = self._settings.get("display", "window_seconds", default=4.0)
            amplitude_range = self._settings.get("display", "amplitude_range", default=100) 

            self.eeg_widget.set_x_range(self._window_time)
            self.eeg_widget.set_y_range(amplitude_range)

            self._raw_data = np.array([])
            self._eeg_data = np.array([])
 

            self._show_board_info(session, name)

        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                QMessageBox.warning(
                    self,
                    "连接超时",
                    f"连接设备超时（{timeout} 秒）。\n请检查设备连接和串口设置。",
                )
            else:
                QMessageBox.critical(
                    self,
                    "连接失败",
                    f"无法连接到设备。\n错误信息：{e}",
                )

    def _show_board_info(self, session: BoardSession, name: str) -> None:
        eeg_names = session.eeg_names
        info_lines = [
            f"设备名称：{name}",
            f"采样率：{session.sampling_rate} Hz",
            f"EEG 通道数：{session.eeg_channel_num}",
        ]
        if eeg_names:
            info_lines.append(f"EEG 通道：{', '.join(eeg_names)}")

        QMessageBox.information(
            self,
            "连接成功",
            "\n".join(info_lines),
        )

    def _on_disconnect(self) -> None:
        self._on_stop()
        if self._session:
            self._session.release()
            self._session = None
        self._control_panel.set_connected(False)

    def _on_start(self) -> None:
        if self._session is None:
            return
        try:
            self._session.start()
            self._control_panel.set_streaming(True)
            self._raw_data = np.array([])
            self._eeg_data = np.array([])
            self._timer.start()
        except Exception:
            traceback.print_exc()

    def _on_stop(self) -> None:
        self._timer.stop()
        if self._session and self._session.is_streaming:
            self._session.stop()
        self._control_panel.set_streaming(False)
        if self._recorder.is_recording:
            self._recorder.stop()
            self._control_panel._record_check.setChecked(False)

    """
    耗时操作全部异步：
    apply_filter_chain()      ──→ 工作线程
    compute_psd_welch()       ──→ 工作线程
    compute_band_powers()     ──→ 工作线程

    留在主线程的都是轻量操作：
    NumPy 切片/拼接            ──→ C 级实现，微秒级
    pyqtgraph setData         ──→ 渲染层已优化
    emit 信号                 ──→ 微秒级投递
    CSV 录制                  ──→ 入队 queue.put() 微秒级，后台 daemon 线程写磁盘
    """
    def _on_timer_tick(self) -> None:
        if self._session is None or not self._session.is_streaming:
            return
        try:
            self._window_time = self._settings.get("display", "window_seconds", default=4.0)
            window_sample_num = int(self._sample_rate * self._window_time)
            # 所有通道数据
            self._raw_data = self._session.get_current_data(window_sample_num)
            # eeg通道数据
            self._eeg_data = self._raw_data[self._eeg_channels[:8], :]

            if self._eeg_data.size > 0 and self._eeg_data.shape[1] > 0:
                t = np.arange(-self._eeg_data.shape[1] + 1, 1) / self._sample_rate
                self.eeg_widget.updata_data(t, self._eeg_data)

        except Exception:
            traceback.print_exc()

    def _on_processed_data(self, result) -> None:
        try:
            if result.psd_freqs.size > 0 and result.psd_values.size > 0:
                self._spectrum_widget.update_spectrum(result.psd_freqs, result.psd_values)
            if result.band_powers:
                self._band_power_widget.update_band_powers(result.band_powers)
        except Exception:
            pass

    def _on_record_toggled(self, checked: bool) -> None:
        if checked:
            if self._session and self._session.is_streaming:
                labels = self._session.eeg_names
                self._recorder.start(labels)
        else:
            self._recorder.stop()

    def _on_config_changed(self, updates: dict) -> None:
        for key, value in updates.items():
            parts = key.split(".")
            self._settings.set(value, *parts)

            if key == "display.window_seconds":
                self.eeg_widget.set_x_range(value)
            elif key == "display.amplitude_range":
                self.eeg_widget.set_y_range(value)
            elif key == "display.refresh_ms":
                self._refresh_ms = value
                self._timer.setInterval(value)


    def _make_filter_config(self) -> FilterConfig:
        return FilterConfig(
            bandpass_low=self._settings.get("process", "bp_low_hz", default=0.1),
            bandpass_high=self._settings.get("process", "bp_high_hz", default=45.0),
            notch=self._settings.get("process", "notch_hz", default=50.0),
            sampling_rate=self._session.sampling_rate if self._session else 250.0,
        )

    def closeEvent(self, event) -> None:
        self._app_settings.setValue("window/geometry", self.saveGeometry())
        self._app_settings.setValue("window/state", self.saveState())

        self._timer.stop()

        if self._recorder.is_recording:
            self._recorder.stop()

        if self._session:
            self._session.release()

        self._processing_thread.quit()
        self._processing_thread.wait(3000)

        try:
            user_path = os.path.join(
                os.path.dirname(__file__), "..", "parameter", "user_settings.json"
            )
            self._settings.save(user_path)
        except Exception:
            pass

        event.accept()
