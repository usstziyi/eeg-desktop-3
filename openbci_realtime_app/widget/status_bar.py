from PySide6.QtWidgets import QStatusBar, QLabel


class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_label = QLabel("Disconnected")
        self._mode_label = QLabel("Mode: Synthetic")
        self._rate_label = QLabel("SR: -- Hz")
        self._buf_label = QLabel("Buf: --")

        self.addWidget(self._status_label, 1)
        self.addPermanentWidget(self._mode_label)
        self.addPermanentWidget(self._rate_label)
        self.addPermanentWidget(self._buf_label)

    def set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def set_mode(self, text: str) -> None:
        self._mode_label.setText(f"Mode: {text}")

    def set_sampling_rate(self, rate: float) -> None:
        self._rate_label.setText(f"SR: {rate:.0f} Hz")

    def set_buffer_status(self, text: str) -> None:
        self._buf_label.setText(f"Buf: {text}")
