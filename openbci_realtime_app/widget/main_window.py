import numpy as np
from PySide6.QtCore import QTimer, QThread, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QWidget,
)

from acquisition import BoardSession, create_board
from parameter import Settings
from processing import FilterConfig, ProcessingWorker
from recording import Recorder

from .control_panel import ControlPanel
from .eeg_plot_widget import EegPlotWidget
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

        self._raw_buffer: np.ndarray = np.array([])
        self._time_buffer: np.ndarray = np.array([])
        self._prev_board_time: float = 0.0
        self._elapsed_time: float = 0.0
        self._psd_counter: int = 0
        self._psd_interval: int = 4
        self._refresh_ms: int = 50

        self._init_ui()
        self._init_timer()
        self._init_processing_thread()

        self._connect_signals()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self._control_panel = ControlPanel()
        main_layout.addWidget(self._control_panel)

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self._eeg_plot = EegPlotWidget()
        right_splitter.addWidget(self._eeg_plot)

        analysis_tabs = QTabWidget()
        self._spectrum_widget = SpectrumWidget()
        self._band_power_widget = BandPowerWidget()
        analysis_tabs.addTab(self._spectrum_widget, "PSD")
        analysis_tabs.addTab(self._band_power_widget, "Band Power")
        right_splitter.addWidget(analysis_tabs)

        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(right_splitter, 1)

        self._init_channels()

    def _init_channels(self) -> None:
        num_channels = 8
        self._eeg_plot.setup_channels(num_channels)
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
            mode = self._settings.get("board", "mode", default="synthetic")
            port = self._settings.get("board", "serial_port", default="COM3")
            timeout = self._settings.get("board", "timeout", default=10)

            board = create_board(mode, serial_port=port, timeout=timeout)
            session = BoardSession(board)
            session.prepare()

            self._session = session
            self._control_panel.set_connected(True)

            window_s = self._settings.get("display", "window_seconds", default=4.0)
            self._eeg_plot.set_window_seconds(window_s)

            y_scale = self._settings.get("display", "y_scale_uv", default=100)
            y_range = y_scale * 2
            self._eeg_plot.set_y_range(-y_range, y_range)

            self._elapsed_time = 0.0
            self._prev_board_time = 0.0
            self._raw_buffer = np.array([])
            self._time_buffer = np.array([])

        except Exception:
            pass

    def _on_disconnect(self) -> None:
        self._on_stop()
        if self._session:
            self._session.release()
            self._session = None
        self._control_panel.set_connected(False)
        self._eeg_plot.setup_channels(8)
        self._spectrum_widget.setup_channels(8)
        self._band_power_widget.setup_channels(8)

    def _on_start(self) -> None:
        if self._session is None:
            return
        try:
            self._session.start()
            self._control_panel.set_streaming(True)
            self._elapsed_time = 0.0
            self._prev_board_time = 0.0
            self._raw_buffer = np.array([])
            self._time_buffer = np.array([])
            self._psd_counter = 0
            self._timer.start()
        except Exception:
            pass

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
            sampling_rate = self._session.sampling_rate
            window_seconds = self._settings.get("display", "window_seconds", default=4.0)
            max_points = int(sampling_rate * window_seconds)
            refresh_points = int(sampling_rate * self._refresh_ms / 1000.0)
            data = self._session.get_current_data(refresh_points * 2)
            if data.size == 0:
                return

            eeg_channels = self._session.eeg_channels
            timestamp_channel = self._session.timestamp_channel
            eeg_data = data[eeg_channels, :]

            if timestamp_channel < data.shape[0]:
                board_times = data[timestamp_channel, :].astype(np.float64)
                if board_times.size > 0 and board_times[-1] > self._prev_board_time:
                    dt = (board_times[-1] - self._prev_board_time) / max(len(board_times), 1)
                    self._prev_board_time = board_times[-1]
                else:
                    dt = 1.0 / sampling_rate
            else:
                dt = 1.0 / sampling_rate

            new_samples = eeg_data.shape[1]
            new_times = self._elapsed_time + np.arange(new_samples) * dt
            self._elapsed_time = new_times[-1] + dt

            if self._raw_buffer.size == 0:
                self._raw_buffer = eeg_data
                self._time_buffer = new_times
            else:
                self._raw_buffer = np.hstack([self._raw_buffer, eeg_data])
                self._time_buffer = np.hstack([self._time_buffer, new_times])

            if self._raw_buffer.shape[1] > max_points:
                trim = self._raw_buffer.shape[1] - max_points
                self._raw_buffer = self._raw_buffer[:, trim:]
                self._time_buffer = self._time_buffer[trim:]

            if self._time_buffer.size > 0:
                t_offset = self._time_buffer[-1] - window_seconds
            else:
                t_offset = 0.0
            display_times = self._time_buffer - t_offset

            self._eeg_plot.update_data(self._raw_buffer, display_times)

            self._psd_counter += 1
            if self._psd_counter >= self._psd_interval:
                self._psd_counter = 0
                psd_window_s = self._settings.get("processing", "psd_window_seconds", default=4.0)
                psd_samples = int(sampling_rate * psd_window_s)
                analysis_data = (
                    self._raw_buffer[:, -psd_samples:]
                    if self._raw_buffer.shape[1] > psd_samples
                    else self._raw_buffer
                )
                if analysis_data.shape[1] >= 64:
                    processing_config = self._make_filter_config()
                    self._processing_worker.update_config(
                        processing_config,
                        psd_window_s,
                        self._settings.get("processing", "welch_overlap_ratio", default=0.5),
                    )
                    self._processing_worker.process(analysis_data.copy(), sampling_rate)

            if self._recorder.is_recording:
                self._recorder.write_samples(eeg_data, sampling_rate)

        except Exception:
            pass

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
        self._refresh_ms = self._settings.get("display", "refresh_ms", default=50)
        self._timer.setInterval(self._refresh_ms)
        window_s = self._settings.get("display", "window_seconds", default=4.0)
        self._eeg_plot.set_window_seconds(window_s)
        y_scale = self._settings.get("display", "y_scale_uv", default=100)
        y_range = y_scale * 2
        self._eeg_plot.set_y_range(-y_range, y_range)
        self._psd_interval = max(4, int(200 / max(self._refresh_ms, 1)))

    def _make_filter_config(self) -> FilterConfig:
        return FilterConfig(
            bandpass_low=self._settings.get("processing", "bandpass_low_hz", default=1.0),
            bandpass_high=self._settings.get("processing", "bandpass_high_hz", default=45.0),
            notch=self._settings.get("processing", "notch_hz", default=50.0),
            sampling_rate=self._session.sampling_rate if self._session else 250.0,
        )

    def closeEvent(self, event) -> None:
        self._timer.stop()

        if self._recorder.is_recording:
            self._recorder.stop()

        if self._session:
            self._session.release()

        self._processing_thread.quit()
        self._processing_thread.wait(3000)

        try:
            self._settings.save()
        except Exception:
            pass

        event.accept()
