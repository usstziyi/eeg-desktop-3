import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from widget import MainWindow
from parameter import load_default_settings


def main() -> None:
    settings = load_default_settings()
    app = QApplication(sys.argv)
    app.setStyle("fusion")
    app.setOrganizationName("NeuroWorkbench")
    app.setApplicationName("NeuroWorkbench")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    window = MainWindow(settings)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
