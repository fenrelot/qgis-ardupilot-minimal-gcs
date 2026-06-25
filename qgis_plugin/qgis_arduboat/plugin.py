from __future__ import annotations

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dock_widget import ArduBoatDockWidget


class ArduBoatPlugin:
    def __init__(self, iface) -> None:
        self.iface = iface
        self.action: QAction | None = None
        self.dock: ArduBoatDockWidget | None = None

    def initGui(self) -> None:
        self.action = QAction(QIcon(), "ArduBoat Control", self.iface.mainWindow())
        self.action.triggered.connect(self.show_dock)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&ArduBoat Control", self.action)

    def unload(self) -> None:
        if self.action is not None:
            self.iface.removePluginMenu("&ArduBoat Control", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None

    def show_dock(self) -> None:
        if self.dock is None:
            self.dock = ArduBoatDockWidget(self.iface.mainWindow(), self.iface)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.show()
        self.dock.raise_()

