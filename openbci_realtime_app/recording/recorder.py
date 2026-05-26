import csv
import os
import queue
import threading
from datetime import datetime

import numpy as np

"""
用户点 Record:
  start() → _writer_loop 启动

 ══════ 录制中 ══════
  主线程: put → put → put → put → put → ...
  写线程:   get → write → get → write → ...

 用户点 Stop Record:
  stop() → _is_recording=False, stop_event.set()
  主线程: join(timeout=5.0)

  写线程: 
    ① 跳出 while not stop_event 循环
    ② get_nowait 收割剩余 1-2 个 batch
    ③ flush + close
    ④ 线程退出

  主线程: join 返回（线程已结束）
"""

class Recorder:
    def __init__(self, directory: str = "recordings", data_type: str = "raw"):
        self._directory = directory
        self._data_type = data_type
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
        filename = os.path.join(self._directory, f"eeg_recording_{self._data_type}_{timestamp}.csv")
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
        # daemon=True + join() 是标准组合：正常停止时 join 等它优雅退出，
        # 异常退出时系统直接回收，不拖泥带水
        self._thread = threading.Thread(target=self._writer_loop, daemon=True)
        # start() 不是直接调用 _writer_loop ，而是向操作系统申请创建一个 真正的 OS 级线程 。
        # 然后 Python 解释器在新线程的上下文中开始执行 self._writer_loop()
        self._thread.start()
        return filename

    def stop(self) -> None:
        if not self._is_recording:
            return
        self._is_recording = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            # daemon=True + join() 是标准组合：正常停止时 join 等它优雅退出，
            # 异常退出时系统直接回收，不拖泥带水
            self._thread.join(timeout=5.0)

    def write_samples(self, data: np.ndarray, timestamps: np.ndarray, marker: int = 0) -> None:
        if not self._is_recording:
            return
        if data.size == 0:
            return
        self._queue.put((data.copy(), timestamps.copy(), marker))

    def _writer_loop(self) -> None:
        # 阶段一：正常运行
        while not self._stop_event.is_set():
            try:
                # 从队列中获取数据，最多等待0.1秒；若超时则抛出 queue.Empty 异常
                # 如果队列有数据立即返回，返回一组
                item = self._queue.get(timeout=0.1)
                self._write_batch(*item)
            except queue.Empty:
                continue
        
        # 阶段二：排空残留数据
        while True:
            try:
                # get_nowait() 非阻塞地收割，直到队列为空
                item = self._queue.get_nowait()
                self._write_batch(*item)
            except queue.Empty:
                break
        
        # 阶段三：安全关闭文件
        if self._writer and self._file:
            try:
                # Python 的 I/O 缓冲区强制写出到底层 OS 缓冲区
                self._file.flush()
            except Exception:
                pass
            # 关闭文件句柄，释放资源
            self._file.close()
        self._file = None
        self._writer = None

    def _write_batch(self, data: np.ndarray, timestamps: np.ndarray, marker: int) -> None:
        if self._writer is None:
            return
        num_samples = data.shape[1]
        for i in range(num_samples):
            row = [f"{timestamps[i]:.6f}"]
            row.extend(f"{data[ch, i]:.6f}" for ch in range(data.shape[0]))
            row.append(str(marker))
            self._writer.writerow(row)
