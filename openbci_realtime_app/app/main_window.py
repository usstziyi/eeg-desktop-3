import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import QTimer, QThread, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QWidget,
)

from acquisition.board_factory import create_board
from acquisition.board_session import BoardSession
from app.control_panel import ControlPanel
from app.eeg_plot_widget import EegPlotWidget
from app.spectrum_widget import SpectrumWidget
from app.band_power_widget import BandPowerWidget
from app.status_bar import StatusBar
from config.settings import Settings
from processing.processor_worker import ProcessingWorker
from processing.types import FilterConfig
from recording.recorder import Recorder

logger = logging.getLogger(__name__)


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

        self._status_bar = StatusBar()
        self.setStatusBar(self._status_bar)

        self._init_channels()

    def _init_channels(self) -> None:
        num_channels = 8
        self._eeg_plot.setup_channels(num_channels)
        self._spectrum_widget.setup_channels(num_channels)
        self._band_power_widget.setup_channels(num_channels)

    def _init_timer(self) -> None:
        self._timer = QTimer(self)
        # 设置定时器为精确计时器模式，确保更准确的定时精度，减少系统调度带来的延迟
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._refresh_ms = self._settings.get("display", "refresh_ms", default=50)
        self._timer.setInterval(self._refresh_ms)
        self._timer.timeout.connect(self._on_timer_tick)

    def _init_processing_thread(self) -> None:
        self._processing_worker = ProcessingWorker()
        self._processing_thread = QThread(self)
        self._processing_worker.moveToThread(self._processing_thread)
        self._processing_thread.start()
        # 将处理线程的结果信号连接到主界面的回调函数，使用队列连接确保线程安全
        # 非阻塞投递信号
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
            self._status_bar.set_status(f"Connected ({mode})")
            self._status_bar.set_mode(mode.capitalize())
            self._status_bar.set_sampling_rate(session.sampling_rate)
            self._status_bar.set_buffer_status("OK")

            window_s = self._settings.get("display", "window_seconds", default=4.0)
            self._eeg_plot.set_window_seconds(window_s)

            y_scale = self._settings.get("display", "y_scale_uv", default=100)
            # * 2 本质是： y_scale_uv 不是"硬上限"，而是"舒适范围"，乘以 2 提供视觉余量
            y_range = y_scale * 2
            self._eeg_plot.set_y_range(-y_range, y_range)

            self._elapsed_time = 0.0
            self._prev_board_time = 0.0
            self._raw_buffer = np.array([])
            self._time_buffer = np.array([])

            logger.info("Board connected: mode=%s, sr=%.0f Hz", mode, session.sampling_rate)
        except Exception as e:
            logger.error("Connection failed: %s", e)
            self._status_bar.set_status(f"Error: {e}")

    def _on_disconnect(self) -> None:
        # 第一步不是断开硬件，而是 先把运行中的一切停下来
        self._on_stop()
        # 第二步断开硬件
        if self._session:
            self._session.release()
            self._session = None
        self._control_panel.set_connected(False)
        self._status_bar.set_status("Disconnected")
        self._status_bar.set_mode("--")
        self._status_bar.set_sampling_rate(0)
        # 在断开连接时 重置所有图表，清空残留的波形数据
        # 创建 8 条新的空曲线
        self._eeg_plot.setup_channels(8)
        self._spectrum_widget.setup_channels(8)
        self._band_power_widget.setup_channels(8)
        logger.info("Board disconnected")

    def _on_start(self) -> None:
        if self._session is None:
            return
        try:
            self._session.start()
            self._control_panel.set_streaming(True)
            self._status_bar.set_status("Streaming")
            self._elapsed_time = 0.0
            self._prev_board_time = 0.0
            self._raw_buffer = np.array([])
            self._time_buffer = np.array([])
            self._psd_counter = 0
            self._timer.start()
            logger.info("Stream started")
        except Exception as e:
            logger.error("Start failed: %s", e)
            self._status_bar.set_status(f"Error: {e}")

    def _on_stop(self) -> None:
        self._timer.stop()
        if self._session and self._session.is_streaming:
            self._session.stop()
        self._control_panel.set_streaming(False)
        self._status_bar.set_status("Connected (stopped)")
        if self._recorder.is_recording:
            self._recorder.stop()
            self._control_panel._record_check.setChecked(False)
        logger.info("Stream stopped")

    """
    耗时操作全部异步：
    apply_filter_chain()      ──→ 工作线程
    compute_psd_welch()       ──→ 工作线程
    compute_band_powers()     ──→ 工作线程

    留在主线程的都是轻量操作：
    NumPy 切片/拼接           ──→ C 级实现，微秒级
    pyqtgraph setData         ──→ 渲染层已优化
    emit 信号                 ──→ 微秒级投递
    """
    def _on_timer_tick(self) -> None:
        if self._session is None or not self._session.is_streaming:
            return
        try:
            sampling_rate = self._session.sampling_rate
            window_seconds = self._settings.get("display", "window_seconds", default=4.0)
            max_points = int(sampling_rate * window_seconds)
            # 计算每次刷新需要获取的数据点数：采样率 × 0.05秒（即50毫秒，与定时器间隔对应）
            refresh_points = int(sampling_rate * self._refresh_ms / 1000.0)
            # 为了安全余量，防止因定时器抖动而丢数据
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

            buf_status = f"{self._raw_buffer.shape[1]}/{max_points}"
            self._status_bar.set_buffer_status(buf_status)

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
                    # 这就是 "调用变投递" ： process() 看起来是方法调用，实际上是个轻量级的信号发射器，
                    # 真正耗时计算通过 Qt 事件队列 跨线程异步调度 到了工作线程。
                    # .copy() 创建独立副本，线程安全
                    self._processing_worker.process(analysis_data.copy(), sampling_rate)

            if self._recorder.is_recording:
                self._recorder.write_samples(eeg_data, sampling_rate)

        except Exception as e:
            logger.exception("Timer tick error: %s", e)

    def _on_processed_data(self, result) -> None:
        try:
            if result.psd_freqs.size > 0 and result.psd_values.size > 0:
                self._spectrum_widget.update_spectrum(result.psd_freqs, result.psd_values)
            if result.band_powers:
                self._band_power_widget.update_band_powers(result.band_powers)
        except Exception as e:
            logger.exception("Processed data update error: %s", e)

    def _on_record_toggled(self, checked: bool) -> None:
        if checked:
            if self._session and self._session.is_streaming:
                labels = self._session.eeg_names
                path = self._recorder.start(labels)
                self._status_bar.set_status(f"Recording: {Path(path).name}")
                logger.info("Recording started: %s", path)
        else:
            self._recorder.stop()
            if self._session and self._session.is_streaming:
                self._status_bar.set_status("Streaming")
            logger.info("Recording stopped")

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
        logger.info("Shutting down...")
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
        logger.info("Shutdown complete")
