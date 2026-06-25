from __future__ import annotations

from pathlib import Path

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsMarkerSymbol,
    QgsPointXY,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

from .track_log import TrackSample

TRACK_LAYER_NAME = "ArduBoat Track"
TRACK_FIELDS = [
    ("time_utc", QVariant.String, 24),
    ("mode", QVariant.String, 16),
    ("lat", QVariant.Double, None),
    ("lon", QVariant.Double, None),
    ("heading", QVariant.Double, None),
    ("speed_ms", QVariant.Double, None),
]


class TrackExportError(RuntimeError):
    pass


class TrackLayer:
    def __init__(self) -> None:
        self.layer: QgsVectorLayer | None = None

    def ensure_layer(self) -> QgsVectorLayer:
        if self.layer is not None and self.layer.isValid():
            return self.layer

        matches = QgsProject.instance().mapLayersByName(TRACK_LAYER_NAME)
        for layer in matches:
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                self.layer = layer
                self._ensure_fields(layer)
                self._style_layer(layer)
                return layer

        layer = QgsVectorLayer("Point?crs=EPSG:4326", TRACK_LAYER_NAME, "memory")
        self._ensure_fields(layer)
        self._style_layer(layer)
        QgsProject.instance().addMapLayer(layer)
        self.layer = layer
        return layer

    def append_sample(self, sample: TrackSample) -> None:
        layer = self.ensure_layer()
        provider = layer.dataProvider()
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(sample.lon, sample.lat)))
        attributes = [None] * len(layer.fields())
        values = {
            "time_utc": sample.timestamp_utc,
            "mode": sample.mode,
            "lat": sample.lat,
            "lon": sample.lon,
            "heading": sample.heading_deg,
            "speed_ms": sample.ground_speed_m_s,
        }
        for field_name, value in values.items():
            index = layer.fields().indexFromName(field_name)
            if index >= 0:
                attributes[index] = value
        feature.setAttributes(attributes)
        provider.addFeature(feature)
        layer.updateExtents()
        layer.triggerRepaint()

    def sample_count(self) -> int:
        if self.layer is None or not self.layer.isValid():
            return 0
        return self.layer.featureCount()

    def clear(self) -> None:
        if self.layer is None or not self.layer.isValid():
            return
        provider = self.layer.dataProvider()
        provider.deleteFeatures([feature.id() for feature in self.layer.getFeatures()])
        self.layer.updateExtents()
        self.layer.triggerRepaint()

    def export_to(self, path: str | Path, driver_name: str) -> None:
        layer = self.ensure_layer()
        if layer.featureCount() == 0:
            raise TrackExportError("track has no samples to save")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = driver_name
        options.fileEncoding = "UTF-8"
        if driver_name == "GPKG":
            options.layerName = "arduboat_track"

        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            str(path),
            QgsProject.instance().transformContext(),
            options,
        )
        error_code = result[0] if isinstance(result, tuple) else result
        message = result[1] if isinstance(result, tuple) and len(result) > 1 else ""
        if error_code != QgsVectorFileWriter.NoError:
            raise TrackExportError(message or f"QGIS writer error {error_code}")

    def _ensure_fields(self, layer: QgsVectorLayer) -> None:
        existing = {field.name() for field in layer.fields()}
        fields = []
        for name, field_type, length in TRACK_FIELDS:
            if name in existing:
                continue
            field = QgsField(name, field_type)
            if length is not None:
                field.setLength(length)
            fields.append(field)
        if fields:
            layer.dataProvider().addAttributes(fields)
            layer.updateFields()

    def _style_layer(self, layer: QgsVectorLayer) -> None:
        symbol = QgsMarkerSymbol.createSimple(
            {
                "name": "circle",
                "color": "0,122,204",
                "outline_color": "255,255,255",
                "outline_width": "0.2",
                "size": "2.2",
            }
        )
        layer.renderer().setSymbol(symbol)
        layer.triggerRepaint()


def format_track_export_path(path: str, driver_name: str) -> str:
    cleaned = path.strip()
    if not cleaned:
        return cleaned
    extension = ".gpkg" if driver_name == "GPKG" else ".shp"
    if not cleaned.lower().endswith(extension):
        cleaned = f"{cleaned}{extension}"
    return cleaned
