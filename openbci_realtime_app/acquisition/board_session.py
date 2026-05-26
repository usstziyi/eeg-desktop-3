import numpy as np
from brainflow.board_shim import BoardShim

BUFFER_SIZE = 15000  # 60s数据


class BoardSession:
    def __init__(self, board: BoardShim):
        self._board = board
        self._board_id = board.get_board_id()
        self._sampling_rate = BoardShim.get_sampling_rate(self._board_id)
        self._eeg_channels = BoardShim.get_eeg_channels(self._board_id)
        self._total_channel_num = BoardShim.get_num_rows(self._board_id)
        self._is_streaming = False
        self._is_prepared = False

    @property
    def board(self) -> BoardShim:
        return self._board

    @property
    def board_id(self) -> int:
        return self._board_id

    @property
    def sampling_rate(self) -> float:
        return self._sampling_rate
    
    @property
    def total_channel_num(self) -> int:
        return self._total_channel_num

    @property
    def eeg_channels(self) -> list[int]:
        return self._eeg_channels

    @property
    def eeg_channel_num(self) -> int:
        return len(self._eeg_channels)

    @property
    def eeg_names(self) -> list[str]:
        return BoardShim.get_eeg_names(self._board_id)

    @property
    def timestamp_channel(self) -> int:
        return BoardShim.get_timestamp_channel(self._board_id)

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    @property
    def is_prepared(self) -> bool:
        return self._is_prepared

    def prepare(self) -> None:
        self._board.prepare_session()
        self._is_prepared = True

    def start(self, buffer_size: int = BUFFER_SIZE) -> None:
        if not self._is_prepared:
            raise RuntimeError("Board not prepared")
        self._board.start_stream(buffer_size, "")
        self._is_streaming = True

    def stop(self) -> None:
        if self._is_streaming:
            try:
                self._board.stop_stream()
            finally:
                self._is_streaming = False

    def release(self) -> None:
        try:
            self.stop()
        finally:
            if self._is_prepared:
                try:
                    self._board.release_session()
                finally:
                    self._is_prepared = False

    def get_current_data(self, num_samples: int) -> np.ndarray:
        if not self._is_streaming:
            return np.array([])
        # 返回的是 所有通道的完整数据包
        return self._board.get_current_board_data(num_samples)

    def get_board_data(self) -> np.ndarray:
        if not self._is_streaming:
            return np.array([])
        return self._board.get_board_data()


"""
[
    package_num,
    EEG1,
    EEG2,
    EEG3,
    EEG4,
    EEG5,
    EEG6,
    EEG7,
    EEG8,
    accel_x,
    accel_y,
    accel_z,
    ...
    timestamp,
    marker
]

['Fp1', 'Fp2', 'C3', 'C4', 'P7', 'P8', 'O1', 'O2']


eeg_channels = BoardShim.get_eeg_channels(board_id)
accel_channels = BoardShim.get_accel_channels(board_id)
timestamp_channel = BoardShim.get_timestamp_channel(board_id)
package_num_channel = BoardShim.get_package_num_channel(board_id)
sampling_rate = BoardShim.get_sampling_rate(board_id)

eeg_data = data[eeg_channels, :]
accel_data = data[accel_channels, :]
timestamps = data[timestamp_channel, :]
package_nums = data[package_num_channel, :]

t = np.arange(-n + 1, 1) / fs
curve.setData(t, eeg)
"""