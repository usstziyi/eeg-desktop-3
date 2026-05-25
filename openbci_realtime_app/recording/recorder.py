import csv
import os
import queue
import threading
import time
from datetime import datetime

import numpy as np


class Recorder:
    def __init__(self, directory: str = "recordings"):
        self._directory = directory
        self._file = None
        self._writer = None
        self._is_recording = False
        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start(self, channel_labels: list[str] | None = None) -> str:
        if self._is_recording:
            return ""
        os.makedirs(self._directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self._directory, f"eeg_recording_{timestamp}.csv")
        self._file = open(filename, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        header = ["timestamp"]
        if channel_labels:
            header += channel_labels
        else:
            header += [f"ch{i}" for i in range(8)]
        header.append("marker")
        self._writer.writerow(header)
        self._is_recording = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._thread.start()
        return filename

    def stop(self) -> None:
        if not self._is_recording:
            return
        self._is_recording = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def write_samples(self, data: np.ndarray, sampling_rate: float = 250.0, marker: int = 0) -> None:
        if not self._is_recording:
            return
        if data.size == 0:
            return
        self._queue.put((data.copy(), sampling_rate, marker))

    def _writer_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.1)
                self._write_batch(*item)
            except queue.Empty:
                continue

        while True:
            try:
                item = self._queue.get_nowait()
                self._write_batch(*item)
            except queue.Empty:
                break

        if self._writer and self._file:
            try:
                self._file.flush()
            except Exception:
                pass
            self._file.close()
        self._file = None
        self._writer = None

    def _write_batch(self, data: np.ndarray, sampling_rate: float, marker: int) -> None:
        if self._writer is None:
            return
        t = time.time()
        num_samples = data.shape[1]
        dt = 1.0 / sampling_rate if sampling_rate > 0 else 0.004
        for i in range(num_samples):
            row = [f"{t + i * dt:.6f}"]
            row.extend(f"{data[ch, i]:.6f}" for ch in range(data.shape[0]))
            row.append(str(marker))
            self._writer.writerow(row)
