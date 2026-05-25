import logging
import sys

from PySide6.QtWidgets import QApplication

from widget.main_window import MainWindow
from parameter.settings import load_default_settings


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting OpenBCI EEG Desktop Application")

    settings = load_default_settings()

    app = QApplication(sys.argv)
    app.setApplicationName("OpenBCI EEG Monitor")

    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
