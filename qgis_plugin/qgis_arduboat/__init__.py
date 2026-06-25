"""QGIS plugin entry point for the ArduBoat operator map."""


def classFactory(iface):
    from .plugin import ArduBoatPlugin

    return ArduBoatPlugin(iface)

