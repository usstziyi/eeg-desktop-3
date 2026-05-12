from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds


def create_board(mode: str, serial_port: str = "", timeout: int = 10) -> BoardShim:
    params = BrainFlowInputParams()
    params.timeout = timeout
    if mode == "synthetic":
        board_id = BoardIds.SYNTHETIC_BOARD.value
    elif mode == "cyton":
        params.serial_port = serial_port
        board_id = BoardIds.CYTON_BOARD.value
    else:
        raise ValueError(f"Unknown board mode: {mode}")
    return BoardShim(board_id, params)
